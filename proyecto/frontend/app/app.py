from flask import Flask, render_template, send_from_directory, url_for, request, redirect, session, jsonify, Response
from functools import wraps
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
import requests
import os
import jwt
import threading
from models_db import Dialogue, Message, create_dialogue, get_dialogue_by_name, add_message
import datetime

# Login/forms
from forms import LoginForm, RegisterForm

# Database-backed users
from models_db import db, User, get_user_by_email, create_user

app = Flask(__name__, static_url_path='')
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)  # Para mantener la sesión

# Configurar el secret_key. OJO, no debe ir en un servidor git público.
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'dev-secret-change-me-ssdd-2526-ok')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///frontend.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db.init_app(app)
# Ensure tables are created when the app module is imported (works with flask run)
with app.app_context():
    db.create_all()

# Simple counters for metrics
app.metrics = {'chat_requests_total': 0}


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm(None if request.method != 'POST' else request.form)
    error = None
    if request.method == 'POST' and form.validate():
        if get_user_by_email(form.email.data):
            error = 'User already exists'
        else:
            create_user(form.name.data, form.email.data, form.password.data)
            return redirect(url_for('login'))
    return render_template('register.html', form=form, error=error)


def generate_jwt(user_id, expire_minutes=30):
    payload = {
        'sub': int(user_id),
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token


def get_auth_token_from_request():
    # Prefer Authorization header, fallback to session
    auth = request.headers.get('Authorization')
    if auth and auth.lower().startswith('bearer '):
        return auth.split(None, 1)[1]
    return session.get('jwt_token')


def require_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_auth_token_from_request()
        if not token:
            return jsonify({'error': 'missing token'}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'token expired'}), 401
        except Exception:
            return jsonify({'error': 'invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


def get_auth_headers():
    token = get_auth_token_from_request()
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers

def decode_jwt(token):
    return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])

def serialize_message(m):
    return {
        'role': m.role,
        'content': m.content,
        'timestamp': m.timestamp.isoformat() if m.timestamp else None
    }

def serialize_dialogue(d):
    return {
        'id': d.id,
        'name': d.name,
        'status': d.status,
        'created_at': d.created_at.isoformat() if d.created_at else None,
        'messages': [serialize_message(m) for m in d.messages]
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    error = None
    form = LoginForm(None if request.method != 'POST' else request.form)
    if request.method == "POST" and form.validate():
        user = get_user_by_email(form.email.data)
        if not user or not user.check_password(form.password.data):
            error = 'Invalid Credentials. Please try again.'
        else:
            login_user(user, remember=form.remember_me.data)
            # generate JWT and store in session
            token = generate_jwt(user.id)
            session['jwt_token'] = token
            # active users metric comes from DB when scraped
            return redirect(url_for('index'))

    return render_template('login.html', form=form, error=error)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('jwt_token', None)
    return redirect(url_for('index'))


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


@app.route('/chat')
@login_required
def chat():
    # Regenerar JWT si falta de la sesión (ej: tras hot-reload del servidor en debug)
    if not session.get('jwt_token'):
        session['jwt_token'] = generate_jwt(current_user.id)
    return render_template('chat.html', user_id=current_user.id, jwt_token=session.get('jwt_token'))


@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    prompt = request.form.get('prompt')
    if not prompt:
        return redirect(url_for('chat'))
    app.metrics['chat_requests_total'] += 1

    prompt_service = os.environ.get('PROMPT_SERVICE_URL', 'http://localhost:8180/prompt')
    headers = {}
    token = session.get('jwt_token')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        resp = requests.post(prompt_service, json={'prompt': prompt}, headers=headers, timeout=10)
    except requests.RequestException as e:
        return render_template('chat.html', error=str(e), prompt=prompt)

    # Basic handling of common responses
    if resp.status_code in (200, 201):
        try:
            data = resp.json()
        except Exception:
            data = {'answer': resp.text}
        answer = data.get('answer') or data.get('response') or resp.text
        return render_template('chat.html', answer=answer, prompt=prompt)
    elif resp.status_code == 202:
        location = resp.headers.get('Location')
        return render_template('chat.html', prompt=prompt, info='Processing', location=location)
    else:
        return render_template('chat.html', prompt=prompt, error=f'Upstream error: {resp.status_code} {resp.text}')


# --- REST API endpoints (JSON) ---


@app.route('/api/u/<int:user_id>/dialogue', methods=['GET'])
@login_required
def api_get_dialogue(user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    dialogues = Dialogue.query.filter_by(user_id=user_id).all()
    return jsonify({'dialogues': [serialize_dialogue(d) for d in dialogues]})



@app.route('/api/u/<int:user_id>/dialogue', methods=['POST'])
@login_required
def api_create_dialogue(user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    data = request.get_json(silent=True) or {}
    name = data.get('name') or f'dialogue-{user_id}'
    dlg = create_dialogue(user, name)
    return jsonify({'dialogue': serialize_dialogue(dlg)}), 201


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>', methods=['GET'])
@login_required
def api_get_one_dialogue(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    dlg = get_dialogue_by_name(user, dname)
    if not dlg:
        return jsonify({'error': 'dialogue not found'}), 404
    return jsonify({'dialogue': serialize_dialogue(dlg)})


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>', methods=['DELETE'])
@login_required
def api_delete_dialogue(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
        
    # Eliminar de la BD local de SQLite
    dlg = get_dialogue_by_name(user, dname)
    if dlg:
        Message.query.filter_by(dialogue_id=dlg.id).delete()
        db.session.delete(dlg)
        db.session.commit()
        
    # Intentar eliminar también del backend REST Java
    prompt_service = os.environ.get('PROMPT_SERVICE_URL', 'http://localhost:8180/prompt')
    backend_url = prompt_service.replace("/chat", f"/u/{user_id}/dialogue/{dname}")
    try:
        requests.delete(backend_url, timeout=10)
    except Exception:
        pass

    return jsonify({'status': 'deleted'})


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>/next', methods=['POST'])
@login_required
def api_dialogue_next(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    dlg = get_dialogue_by_name(user, dname)
    if not dlg:
        return jsonify({'error': 'dialogue not found'}), 404

    data = request.get_json(silent=True) or {}
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'missing prompt'}), 400

    if dlg.status in ('BUSY', 'FINISHED'):
        return '', 204

    # Mark as BUSY and save user message
    dlg.status = 'BUSY'
    db.session.commit()
    add_message(dlg, 'user', prompt)

    # background worker to call prompt service and add assistant message
    prompt_service = os.environ.get('PROMPT_SERVICE_URL', 'http://localhost:8180/prompt')

    def worker(dialogue_id, prompt_text):
        try:
            resp = requests.post(
                prompt_service,
                json={'prompt': prompt_text},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            content = None
            if resp.status_code in (200, 201):
                try:
                    rdata = resp.json()
                    # ChatEndpoint devuelve PromptResponseDTO con campo 'message'
                    content = rdata.get('message') or rdata.get('answer') or rdata.get('response') or resp.text
                except Exception:
                    content = resp.text
            else:
                content = f'Upstream error {resp.status_code}: {resp.text}'
            # re-open app context to access DB
            with app.app_context():
                dlg2 = Dialogue.query.get(dialogue_id)
                if dlg2:
                    add_message(dlg2, 'assistant', content)
                    dlg2.status = 'READY'
                    db.session.commit()
        except Exception as ex:
            with app.app_context():
                dlg2 = Dialogue.query.get(dialogue_id)
                if dlg2:
                    add_message(dlg2, 'assistant', f'Error contacting prompt service: {ex}')
                    dlg2.status = 'READY'
                    db.session.commit()

    t = threading.Thread(target=worker, args=(dlg.id, prompt))
    t.daemon = True
    t.start()

    return '', 201


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>/end', methods=['POST'])
@login_required
def api_dialogue_end(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404
    dlg = get_dialogue_by_name(user, dname)
    if not dlg:
        return jsonify({'error': 'dialogue not found'}), 404
    dlg.status = 'FINISHED'
    db.session.commit()
    return jsonify({'status': 'finished'})


@app.route('/api/chat/send', methods=['POST'])
@login_required
def api_chat_send():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'missing prompt'}), 400

    prompt_service = os.environ.get('PROMPT_SERVICE_URL', 'http://localhost:8180/prompt')
    try:
        resp = requests.post(prompt_service, json={'prompt': prompt},
                             headers={'Content-Type': 'application/json'}, timeout=10)
    except requests.RequestException as e:
        return jsonify({'error': 'upstream error', 'detail': str(e)}), 502

    content_type = resp.headers.get('Content-Type', 'application/json')
    return Response(resp.content, status=resp.status_code, content_type=content_type)



@app.route('/metrics')
def metrics():
    # Return simple Prometheus plain-text metrics
    lines = []
    lines.append('# HELP ssdd_chat_requests_total Number of chat requests')
    lines.append('# TYPE ssdd_chat_requests_total counter')
    lines.append(f"ssdd_chat_requests_total {app.metrics['chat_requests_total']}")
    lines.append('# HELP ssdd_active_users Current number of registered users')
    lines.append('# TYPE ssdd_active_users gauge')
    try:
        users_count = User.query.count()
    except Exception:
        users_count = 0
    lines.append(f"ssdd_active_users {users_count}")
    return "\n".join(lines), 200, {'Content-Type': 'text/plain; version=0.0.4'}


if __name__ == '__main__':
    # Ensure DB tables exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5010)))
