from datetime import date

from app.models import User
from flask import url_for
from flask_wtf import FlaskForm  # ignore
from wtforms.fields import EmailField  # ignore
from wtforms.fields import (BooleanField, PasswordField, SelectField,
                            StringField, SubmitField, TextAreaField)
from wtforms.validators import InputRequired  # ignore
from wtforms.validators import Email, EqualTo, Length, ValidationError


class PrivacyForm(FlaskForm):
    is_public = SelectField(
        " Hide from external search engines and non-registered users?",
        choices=[("Yes", "Yes"), ("No", "No")],
    )
    hide_profile = SelectField(
        " Hide profile from everyone? ", choices=[("Yes", "Yes"), ("No", "No")]
    )


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), Length(1, 64), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember_me = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")


class RegistrationForm(FlaskForm):
    username = StringField("Unique username", validators=[InputRequired()])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username not available. Choose another username")

    first_name = StringField("First name", validators=[InputRequired(), Length(1, 64)])
    last_name = StringField("Last name", validators=[InputRequired(), Length(1, 64)])
    email = EmailField("Email", validators=[InputRequired(), Length(1, 64), Email()])
    sex = SelectField("Gender", choices=[("Male", "Male"), ("Female", "Female")])
    date_of_birth = StringField("Date of birth", validators=[InputRequired(), Length(1, 64)])

    password = PasswordField(
        "Password",
        validators=[InputRequired(), EqualTo("password2", "Passwords must match")],
    )
    password2 = PasswordField("Confirm password", validators=[InputRequired()])
    submit = SubmitField("Register")

class UpdateDetailsForm(FlaskForm):
    first_name = StringField("First name", validators=[InputRequired(), Length(1, 64)])
    last_name = StringField("Last name", validators=[InputRequired(), Length(1, 64)])
    date_of_birth = StringField("Date of birth", validators=[InputRequired(), Length(1, 64)])
    

class RequestResetPasswordForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), Length(1, 64), Email()])

    # We don't validate the email address so we don't confirm to attackers
    # that an account with the given email exists.


class ResetPasswordForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), Length(1, 64), Email()])
    new_password = PasswordField(
        "New password",
        validators=[InputRequired(), EqualTo("new_password2", "Passwords must match.")],
    )
    new_password2 = PasswordField("Confirm new password", validators=[InputRequired()])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError("Unknown email address.")


class CreatePasswordForm(FlaskForm):
    password = PasswordField(
        "Password",
        validators=[InputRequired(), EqualTo("password2", "Passwords must match.")],
    )
    password2 = PasswordField("Confirm new password", validators=[InputRequired()])


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField("Old password", validators=[InputRequired()])
    new_password = PasswordField(
        "New password",
        validators=[InputRequired(), EqualTo("new_password2", "Passwords must match.")],
    )
    new_password2 = PasswordField("Confirm new password", validators=[InputRequired()])


class ChangeEmailForm(FlaskForm):
    email = EmailField(
        "New email", validators=[InputRequired(), Length(1, 64), Email()]
    )
    password = PasswordField("Password", validators=[InputRequired()])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email already registered.")


class ChangeUsernameForm(FlaskForm):
    username = StringField("New username", validators=[InputRequired(), Length(1, 64)])
    password = PasswordField("Password", validators=[InputRequired()])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Username already exist, try a different one.")

