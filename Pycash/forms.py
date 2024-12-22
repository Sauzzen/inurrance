from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
import sqlite3

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
