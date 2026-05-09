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


# Nota: Dialogue y Message se eliminaron de SQLite.
# El backend REST Java (MySQL) es la única fuente de verdad para diálogos y mensajes.