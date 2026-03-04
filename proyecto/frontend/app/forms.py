from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField)
from wtforms.validators import InputRequired, Length, Email


class LoginForm(FlaskForm):
    email = StringField('email', validators=[Email(), InputRequired()])
    password = PasswordField('password', validators=[InputRequired()])
    remember_me = BooleanField('remember_me')


class RegisterForm(FlaskForm):
    name = StringField('name', validators=[InputRequired(), Length(min=2)])
    email = StringField('email', validators=[Email(), InputRequired()])
    password = PasswordField('password', validators=[InputRequired(), Length(min=4)])

