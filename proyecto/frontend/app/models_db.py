from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import hashlib

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        if isinstance(password, str):
            password = password.encode('utf-8')
        self.password = hashlib.sha256(password).hexdigest()

    def check_password(self, password):
        if isinstance(password, str):
            password = password.encode('utf-8')
        return self.password == hashlib.sha256(password).hexdigest()

# Helper functions

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def create_user(name, email, password, is_admin=False):
    user = User(name=name, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


class Dialogue(db.Model):
    __tablename__ = 'dialogues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='READY')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('dialogues', lazy=True))
    messages = db.relationship('Message', backref='dialogue', lazy=True, cascade='all, delete-orphan')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    dialogue_id = db.Column(db.Integer, db.ForeignKey('dialogues.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())


def create_dialogue(user, name):
    dlg = Dialogue(name=name, user=user, status='READY')
    db.session.add(dlg)
    db.session.commit()
    return dlg


def get_dialogue_by_name(user, name):
    return Dialogue.query.filter_by(user_id=user.id, name=name).first()


def add_message(dialogue, role, content):
    m = Message(dialogue=dialogue, role=role, content=content)
    db.session.add(m)
    db.session.commit()
    return m
### End Patch