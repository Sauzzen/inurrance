from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
import sqlite3
import hashlib

# Hash password function
def hash_password(password):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(password.encode('utf-8'))
    return sha256_hash.hexdigest()

# Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

    def validate_email(self, email):
        conn = sqlite3.connect('login.db')
        curs = conn.cursor()
        curs.execute("SELECT email FROM login WHERE email = ?", [email.data])
        valemail = curs.fetchone()
        if valemail is None:
            raise ValidationError('This Email ID is not registered. Please register before login')

# Forget Password Form
class ForgetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')

# Sign Up Form
class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Register as Admin')  # Admin registration checkbox
    submit = SubmitField('Register')

    def validate_email(self, email):
        conn = sqlite3.connect('login.db')
        curs = conn.cursor()
        curs.execute("SELECT email FROM login WHERE email = ?", [email.data])
        valemail = curs.fetchone()
        if valemail:
            raise ValidationError('Email already exists. Please use a different email.')

    def hash_password_on_submit(self):
        if self.password.data:
            return hash_password(self.password.data)  # Hash the password during form submission
        return None
