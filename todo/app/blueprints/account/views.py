import logging
from typing import Optional, List, Dict

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, login_required, logout_user
from app import compress, db
from app.blueprints.account.forms import (
    ChangeEmailForm, ChangePasswordForm, ChangeUsernameForm, CreatePasswordForm, 
    LoginForm, RegistrationForm, RequestResetPasswordForm, ResetPasswordForm, 
    UpdateDetailsForm
)
from app.models.user import User
from app.utils import SendEmailClient

# Initialize the Blueprint
account = Blueprint("account", __name__)

# Email client
send_email = SendEmailClient()

# Constants
_ACCOUNT_MANAGE = "tasks.all_tasks"
_ACCOUNT_INVALID_LOGIN_MESSAGE = "Invalid email or password."

@account.route("/login", methods=["GET", "POST"])
@compress.compressed()
def login():
    """Log in an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))

    form = LoginForm()
    if form.validate_on_submit():
        user: Optional[User] = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash("You are now logged in. Welcome back!", "success")
            next_page = request.args.get("next") or url_for(_ACCOUNT_MANAGE)
            return redirect(next_page)
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")

    return render_template("login.html", form=form)

@account.route("/register", methods=["GET", "POST"])
@compress.compressed()
def register():
    """Register a new user, and send them a confirmation email."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            date_of_birth=form.date_of_birth.data
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_confirmation_token()
        confirm_link = url_for("account.confirm", token=token, _external=True)
        template = render_template("confirm.html", user=user, confirm_link=confirm_link)

        send_email.delay(
            recipient=user.email,
            subject="Confirm Your Account",
            template=template
        )

        flash(f"A confirmation link has been sent to {user.email}.", "warning")
        return redirect(url_for(_ACCOUNT_MANAGE))

    return render_template("register.html", form=form)

@account.route("/logout")
@compress.compressed()
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for(_ACCOUNT_MANAGE))

@account.route("/reset-password", methods=["GET", "POST"])
@compress.compressed()
def reset_password_request():
    """Respond to existing user's request to reset their password."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))

    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            reset_link = url_for("account.reset_password", token=token, _external=True)
            template = render_template("reset_password.html", user=user, reset_link=reset_link)

            send_email.delay(
                recipient=user.email,
                subject="Reset Your Password",
                template=template
            )

        flash(f"A password reset link has been sent to {form.email.data}.", "warning")
        return redirect(url_for("account.login"))

    return render_template("reset_password_request.html", form=form)

@account.route("/reset-password/<token>", methods=["GET", "POST"])
@compress.compressed()
def reset_password(token):
    """Reset an existing user's password."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.reset_password(token, form.new_password.data):
            flash("Your password has been updated.", "success")
            return redirect(url_for("account.login"))
        else:
            flash("The password reset link is invalid or has expired.", "error")

    return render_template("reset_password.html", form=form)

@account.route("/manage/change-password", methods=["GET", "POST"])
@login_required
@compress.compressed()
def change_password():
    """Change an existing user's password."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            db.session.commit()
            flash("Your password has been updated.", "success")
            return redirect(url_for(_ACCOUNT_MANAGE))
        else:
            flash("Original password is invalid.", "error")

    return render_template("all_tasks.html", form=form)

@account.route("/manage/change-username", methods=["GET", "POST"])
@login_required
@compress.compressed()
def change_username_request():
    """Respond to existing user's request to change their username."""
    form = ChangeUsernameForm(obj=current_user)
    first_time_change = current_user.username is None

    if form.validate_on_submit():
        if current_user.verify_password(form.password.data, first_time_change):
            current_user.username = form.username.data
            db.session.add(current_user)
            db.session.commit()
            flash(f"Username changed to {current_user.username}.", "success")
            return redirect(url_for(_ACCOUNT_MANAGE))
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")

    return render_template("all_tasks.html", form=form)

@account.route("/manage/update-details", methods=["GET", "POST"])
@login_required
@compress.compressed()
def update_details():
    """Update user account details."""
    form = UpdateDetailsForm(obj=current_user)

    if form.validate_on_submit():
        for field, value in form.data.items():
            if field != "csrf_token":
                setattr(current_user, field, value)

        db.session.add(current_user)
        db.session.commit()
        flash("Details updated successfully.", "success")
        return redirect(url_for(_ACCOUNT_MANAGE))

    return render_template("all_tasks.html", form=form)

@account.route("/manage/change-email", methods=["GET", "POST"])
@login_required
@compress.compressed()
def change_email_request():
    """Respond to existing user's request to change their email."""
    form = ChangeEmailForm()

    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            change_email_link = url_for("account.change_email", token=token, _external=True)
            template = render_template("change_email.html", user=current_user, change_email_link=change_email_link)

            send_email.delay(
                recipient=new_email,
                subject="Confirm Your New Email",
                template=template
            )

            flash(f"A confirmation link has been sent to {new_email}.", "warning")
            return redirect(url_for(_ACCOUNT_MANAGE))
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")

    return render_template("all_tasks.html", form=form)

@account.route("/manage/change-email/<token>")
@login_required
@compress.compressed()
def change_email(token):
    """Change existing user's email with provided token."""
    if current_user.change_email(token):
        flash("Your email address has been updated.", "success")
    else:
        flash("The confirmation link is invalid or has expired.", "error")

    return redirect(url_for(_ACCOUNT_MANAGE))

@account.route("/confirm-account")
@login_required
@compress.compressed()
def confirm_request():
    """Respond to new user's request to confirm their account."""
    token = current_user.generate_confirmation_token()
    confirm_link = url_for("account.confirm", token=token, _external=True)
    template = render_template("confirm.html", user=current_user, confirm_link=confirm_link)

    logging.info(f"Confirmation link is: {confirm_link}")

    send_email.delay(
        recipient=current_user.email,
        subject="Confirm Your Account",
        template=template
    )

    flash(f"A new confirmation link has been sent to {current_user.email}.", "success")
    return redirect(url_for(_ACCOUNT_MANAGE))

@account.route("/confirm-account/<token>")
@login_required
@compress.compressed()
def confirm(token):
    """Confirm new user's account with provided token."""
    if current_user.confirmed:
        return redirect(url_for(_ACCOUNT_MANAGE))

    if current_user.confirm_account(token):
        flash("Your account has been confirmed.", "success")
    else:
        flash("The confirmation link is invalid or has expired.", "error")

    return redirect(url_for(_ACCOUNT_MANAGE))

# @account.before_app_request
# @account.before_app_request
# def before_request():
#     """Ensure user confirms their email before accessing protected routes."""
#     if (
#         request.endpoint
#         and current_user.is_authenticated
#         and not current_user.confirmed
#         and not request.endpoint.startswith("account")
#         and request.endpoint != "static"
#     ):
#         return redirect(url_for("account.unconfirmed"))

# Uncomment the lines below to enforce preflight checks for user profile completion


# def check_username_status():
#     """Force user to set up a username and profile data before accessing the site."""
#     if (
#         request.endpoint
#         and current_user.is_authenticated
#         and not current_user.username
#         and not request.endpoint.startswith("account")
#         and request.endpoint != "static"
#     ):
#         flash("Please set up a username and profile data to continue.", "warning")
#         return redirect(url_for("account.change_username_request"))

# @account.route("/unconfirmed")
# def unconfirmed():
#     """Redirect users with unconfirmed emails to a notice page."""
#     if current_user.is_anonymous or current_user.confirmed:
#         return redirect(url_for(_ACCOUNT_MANAGE))
#     return render_template("unconfirmed.html")
