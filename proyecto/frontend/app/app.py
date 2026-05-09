from flask import Flask, render_template, send_from_directory, url_for, request, redirect, session, jsonify, Response
from functools import wraps
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from prometheus_client import Counter
from prometheus_flask_exporter import PrometheusMetrics
import requests
import os
import jwt
import threading
import time
# Dialogue/Message ya no se almacenan en SQLite; el backend REST Java es la fuente de verdad
import datetime

# Login/forms
from forms import LoginForm, RegisterForm

# Database-backed users
from models_db import db, User, get_user_by_email, create_user

app = Flask(__name__, static_url_path='')
# Instrumentación automática de todas las rutas (latencias, códigos HTTP, etc.)
metrics = PrometheusMetrics(app)
print("Prometheus metrics initialized on /metrics")
# Métrica de negocio personalizada: número de peticiones al chat
CHAT_REQUESTS = Counter('ssdd_chat_requests_total', 'Number of chat prompt requests')
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
            try:
                base = _backend_rest_base()
                resp = requests.post(f"{base}/u", 
                                  json={'email': form.email.data, 
                                        'password': form.password.data,
                                        'name': form.name.data},
                                  timeout=10)
                if resp.status_code == 201:
                    java_user = resp.json()
                    user_id = int(java_user['id'])
                    # Create in local SQLite with the same ID
                    user = User(id=user_id, name=form.name.data, email=form.email.data)
                    user.set_password(form.password.data)
                    db.session.add(user)
                    db.session.commit()
                    return redirect(url_for('login'))
                else:
                    error = f"Backend error: {resp.text}"
            except Exception as e:
                error = f"Connection error to backend: {e}"
    return render_template('register.html', form=form, error=error)


def generate_jwt(email, expire_minutes=30):
    payload = {
        'sub': email,
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

def _backend_rest_base():
    url = os.environ.get('PROMPT_SERVICE_URL', 'http://localhost:8080/Service/chat')
    return url.rsplit('/chat', 1)[0]

def _proxy_get(url, token):
    """Proxy GET al backend REST Java y devuelve un Response de Flask."""
    try:
        r = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
        return r.json(), r.status_code
    except Exception as ex:
        return {'error': str(ex)}, 502


def _proxy_post(url, body, token):
    """Proxy POST al backend REST Java y devuelve (json, status_code)."""
    try:
        r = requests.post(url, json=body,
                          headers={'Content-Type': 'application/json',
                                   'Authorization': f'Bearer {token}'},
                          timeout=120)
        try:
            return r.json(), r.status_code
        except Exception:
            return r.text, r.status_code
    except Exception as ex:
        return {'error': str(ex)}, 502


def _proxy_delete(url, token):
    """Proxy DELETE al backend REST Java."""
    try:
        r = requests.delete(url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
        try:
            return r.json(), r.status_code
        except Exception:
            return {}, r.status_code
    except Exception as ex:
        return {'error': str(ex)}, 502


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
            # generate JWT and store in session (backend Java expects email as subject)
            token = generate_jwt(user.email)
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


@app.route('/logs')
@login_required
def logs():
    if not session.get('jwt_token'):
        session['jwt_token'] = generate_jwt(current_user.email)
    return render_template('logs.html', user_id=current_user.id, jwt_token=session.get('jwt_token'))


@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html')


@app.route('/chat')
@login_required
def chat():
    # Regenerar JWT si falta de la sesión (ej: tras hot-reload del servidor en debug)
    if not session.get('jwt_token'):
        session['jwt_token'] = generate_jwt(current_user.email)
    return render_template('chat.html', user_id=current_user.id, jwt_token=session.get('jwt_token'))


@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    prompt = request.form.get('prompt')
    if not prompt:
        return redirect(url_for('chat'))
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


# ---------------------------------------------------------------------------
# API /api/u/<id>/dialogue/... — proxies directos al backend REST Java.
# El backend Java (MySQL) es la única fuente de verdad para diálogos y mensajes.
# ---------------------------------------------------------------------------

@app.route('/api/u/<int:user_id>/dialogue', methods=['GET'])
@login_required
def api_get_dialogue(user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    token = session.get('jwt_token') or generate_jwt(current_user.email)
    base = _backend_rest_base()
    data, status = _proxy_get(f"{base}/u/{user_id}/dialogue", token)
    return jsonify(data), status


@app.route('/api/u/<int:user_id>/dialogue', methods=['POST'])
@login_required
def api_create_dialogue(user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    token = session.get('jwt_token') or generate_jwt(current_user.email)
    body = request.get_json(silent=True) or {}
    base = _backend_rest_base()
    data, status = _proxy_post(f"{base}/u/{user_id}/dialogue", body, token)
    return jsonify(data), status


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>', methods=['GET'])
@login_required
def api_get_one_dialogue(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    token = session.get('jwt_token') or generate_jwt(current_user.email)
    base = _backend_rest_base()
    data, status = _proxy_get(f"{base}/u/{user_id}/dialogue/{dname}", token)
    return jsonify(data), status


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>', methods=['DELETE'])
@login_required
def api_delete_dialogue(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    token = session.get('jwt_token') or generate_jwt(current_user.email)
    base = _backend_rest_base()
    data, status = _proxy_delete(f"{base}/u/{user_id}/dialogue/{dname}", token)
    return jsonify(data), status


def execute_background_task(app, uid, dname_str, prompt_text, token):
    """Llama al backend REST Java en un hilo separado.
    Java gestiona BUSY→READY y guarda mensajes en MySQL.
    El frontend lee el estado vía proxy (no guarda nada en SQLite).
    """
    try:
        with app.app_context():
            base = _backend_rest_base()
        app.logger.info(f"[WORKER] POST {base}/u/{uid}/dialogue/{dname_str}/next")
        requests.post(
            f"{base}/u/{uid}/dialogue/{dname_str}/next",
            json={'prompt': prompt_text},
            headers={'Content-Type': 'application/json',
                     'Authorization': f'Bearer {token}'},
            timeout=120
        )
        app.logger.info(f"[WORKER] Backend respondió OK para user={uid} dialogue={dname_str}")
    except Exception as ex:
        app.logger.error(f"[WORKER] Error contactando backend: {ex}")


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>/next', methods=['POST'])
@login_required
def api_dialogue_next(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'missing prompt'}), 400

    CHAT_REQUESTS.inc()

    jwt_token = session.get('jwt_token') or generate_jwt(current_user.email)
    t = threading.Thread(
        target=execute_background_task,
        args=(app, user_id, dname, prompt, jwt_token)
    )
    t.daemon = True
    t.start()
    return '', 201


@app.route('/api/u/<int:user_id>/dialogue/<string:dname>/end', methods=['POST'])
@login_required
def api_dialogue_end(user_id, dname):
    if current_user.id != user_id:
        return jsonify({'error': 'forbidden'}), 403
    token = session.get('jwt_token') or generate_jwt(current_user.email)
    base = _backend_rest_base()
    data, status = _proxy_post(f"{base}/u/{user_id}/dialogue/{dname}/end", {}, token)
    return jsonify(data), status


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



# /metrics es creado automáticamente por PrometheusMetrics(app)


if __name__ == '__main__':
    # Ensure DB tables exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5010)))
