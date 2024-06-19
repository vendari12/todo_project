from app import compress, db
from app.blueprints.account.forms import (
    ChangeEmailForm,
    ChangePasswordForm,
    ChangeUsernameForm,
    CreatePasswordForm,
    LoginForm,
    RegistrationForm,
    RequestResetPasswordForm,
    ResetPasswordForm,
    UpdateDetailsForm,
    AddAccountSettingsForm,
)
from app.common.email import send_email
from app.models import User, UserSetting, NotificationIntervalEnum
from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_user  # ignore
from flask_login import current_user, login_required, logout_user
import logging
from .utils import oauth_get_user_or_create
from app.common.utils import jsonify_object

account = Blueprint("account", __name__)

oauth = OAuth(current_app)

_ACCOUNT_MANAGE = "account.manage"
_ACCOUNT_INVALID_LOGIN_MESSAGE = "Invalid email or password."


@account.route("/login", methods=["GET", "POST"])
@compress.compressed()
def login():
    """Log in an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if (
            user is not None
            and user.password_hash is not None
            and user.verify_password(form.password.data)
        ):
            login_user(user, form.remember_me.data)
            flash("You are now logged in. Welcome back!", "success")
            if current_user.preferences.count() > 0:
                end_url = url_for("messaging_manager.matches")
            else:
                end_url = url_for(_ACCOUNT_MANAGE)
            return redirect(request.args.get("next") or end_url)
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")
    return render_template("socialite/account/form-login.html", form=form)


@account.route("/register", methods=["GET", "POST"])
@compress.compressed()
def register():
    """Register a new user, and send them a confirmation email."""
    if current_user.is_authenticated:
        return redirect(url_for(_ACCOUNT_MANAGE))
    form = RegistrationForm()
    if form.validate_on_submit():
        user: User = User(
            first_name=form.first_name.data,
            email=form.email.data,
            password=form.password.data,
            current_status=form.current_status.data,
            username=form.username.data,
            DOB=form.DOB.data,
            sex=form.sex.data,
            last_name=form.last_name.data,
        )
        db.session.add(user)
        db.session.commit()
        token: str = user.generate_confirmation_token()
        confirm_link = url_for("account.confirm", token=token, _external=True)
        template = render_template(
            "account/email/confirm.html", user=user, confirm_link=confirm_link
        )
        send_email.delay(
            recipient=user.email,
            subject="Confirm Your Account",
            template=template,
        )
        flash("A confirmation link has been sent to {}.".format(user.email), "warning")
        return redirect(url_for(_ACCOUNT_MANAGE))
    return render_template("socialite/account/form-register.html", form=form)


"""OAuth implementations"""


@account.route("/google/")
@compress.compressed()
def google():
    """
    Google Oauth Config
    Get client_id and client_secret from environment variables
    For developement purpose you can directly put it here inside double quotes"""
    oauth.register(
        name="google",
        client_id=current_app.config["GOOGLE_CLIENT_ID"],
        client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=current_app.config["GOOGLE_CONF_URL"],
        client_kwargs={"scope": "openid email profile"},
    )

    # Redirect to google_auth function
    redirect_uri = url_for("account.google_auth", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@account.route("/google/auth/")
@compress.compressed()
def google_auth():
    """Callback for authenticating user redirected from google Oauth"""
    try:
        token = oauth.google.authorize_access_token()
        user = oauth.google.parse_id_token(
            token=token, nonce=token["userinfo"].get("nonce")
        )
        user_in_db = oauth_get_user_or_create(email=user["email"], token=user, db=db)
        login_user(user_in_db, remember=True)
        flash(f"Welcome, good to have you. {user_in_db.full_name()}", "success")
        return redirect(url_for(_ACCOUNT_MANAGE))
    except Exception as e:
        flash("There was a problem with your request, try other options", "error")
        return redirect(url_for("account.login"))


@account.route("/logout")
@compress.compressed()
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for(_ACCOUNT_MANAGE))


@account.route("/manage", methods=["GET", "POST"])
@account.route("/manage/info", methods=["GET", "POST"])
@login_required
@compress.compressed()
def manage():
    """Display a user's account information."""
    return render_template(
        "socialite/account/pages-setting.html", user=current_user, form=None
    )


@account.route("/reset-password", methods=["GET", "POST"])
@compress.compressed()
def reset_password_request():
    """Respond to existing user's request to reset their password."""
    if not current_user.is_anonymous:
        return redirect(url_for(_ACCOUNT_MANAGE))
    form = RequestResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            reset_link = url_for("account.reset_password", token=token, _external=True)
            template = render_template(
                "account/email/reset_password.html",
                user=user,
                reset_link=reset_link,
                next=request.args.get("next"),
            )
            send_email(
                recipient=user.email,
                subject="Reset Your Password",
                template=template,
            )
        flash(
            "A password reset link has been sent to {}.".format(form.email.data),
            "warning",
        )
        return redirect(url_for("account.login"))
    return render_template("socialite/account/reset_password_request.html", form=form)


@account.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset an existing user's password."""
    if not current_user.is_anonymous:
        return redirect(url_for(_ACCOUNT_MANAGE))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash("Invalid email address.", "error")
            return redirect(url_for(_ACCOUNT_MANAGE))
        if user.reset_password(token, form.new_password.data):
            flash("Your password has been updated.", "success")
            return redirect(url_for("account.login"))
        else:
            flash("The password reset link is invalid or has expired.", "error")
            return redirect(url_for(_ACCOUNT_MANAGE))
    return render_template("socialite/account/reset_password.html", form=form)


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
    return render_template("socialite/account/pages-setting.html", form=form)


@account.route("/manage/change-username", methods=["GET", "POST"])
@login_required
@compress.compressed()
def change_username_request():
    """Respond to existing user's request to change their username."""
    user = User.query.filter_by(id=current_user.id).first()
    first = True if user.username == None else False
    form = ChangeUsernameForm(obj=user)
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data, first):
            user.username = form.username.data
            flash("New username changed to {}.".format(user.username), "success")
            db.session.add(user)
            db.session.commit()
            return redirect(url_for(_ACCOUNT_MANAGE))
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")
    return render_template("socialite/account/pages-setting.html", form=form)


@account.route("/manage/update-details", methods=["GET", "POST"])
@login_required
@compress.compressed()
def update_details():
    """Respond to existing user's request to update some account details."""
    user = User.query.filter_by(id=current_user.id).first()
    form = UpdateDetailsForm(obj=user)
    if form.validate_on_submit():
        for field, value in form.data.items():
            if field != "csrf_token":
                setattr(user, field, value)
        db.session.add(user)
        db.session.commit()
        flash("Edited Successfully.", "success")
        return redirect(url_for(_ACCOUNT_MANAGE))
    return render_template("socialite/account/pages-setting.html", form=form)


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
            change_email_link = url_for(
                "account.change_email", token=token, _external=True
            )
            template = render_template(
                "account/email/change_email.html",
                user=current_user._get_current_object(),
                change_email_link=change_email_link,
            )
            send_email.delay(
                recipient=new_email,
                subject="Confirm Your New Email",
                template=template,
            )
            flash(
                "A confirmation link has been sent to {}.".format(new_email), "warning"
            )
            return redirect(url_for(_ACCOUNT_MANAGE))
        else:
            flash(_ACCOUNT_INVALID_LOGIN_MESSAGE, "error")
    return render_template("socialite/account/pages-setting.html", form=form)


@account.route("/manage/change-email/<token>", methods=["GET", "POST"])
@login_required
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
    template = render_template(
        "account/email/confirm.html",
        user=current_user._get_current_object(),
        confirm_link=confirm_link,
    )
    logging.info(f"Confirmation link is: {confirm_link}")
    send_email.delay(
        recipient=current_user.email,
        subject="Confirm Your Account",
        template=template,
        # current_user is a LocalProxy, we want the underlying user object
    )
    flash(
        "A new confirmation link has been sent to {}.".format(current_user.email),
        "success",
    )
    return redirect(url_for(_ACCOUNT_MANAGE))


@account.route("/confirm-account/<token>")
@login_required
def confirm(token):
    """Confirm new user's account with provided token."""
    if current_user.confirmed:
        return redirect(url_for(_ACCOUNT_MANAGE))
    if current_user.confirm_account(token):
        flash("Your account has been confirmed.", "success")
    else:
        flash("The confirmation link is invalid or has expired.", "error")
    return redirect(url_for(_ACCOUNT_MANAGE))


@account.route("/join-from-invite/<int:user_id>/<token>", methods=["GET", "POST"])
def join_from_invite(user_id, token):
    """
    Confirm new user's account with provided token and prompt them to set
    a password.
    """
    if current_user is not None and current_user.is_authenticated:
        flash("You are already logged in.", "error")
        return redirect(url_for(_ACCOUNT_MANAGE))

    new_user = User.query.get(user_id)
    if new_user is None:
        return redirect(404)

    if new_user.password_hash is not None:
        flash("You have already joined.", "error")
        return redirect(url_for(_ACCOUNT_MANAGE))

    if new_user.confirm_account(token):
        form = CreatePasswordForm()
        if form.validate_on_submit():
            new_user.password = form.password.data
            db.session.add(new_user)
            db.session.commit()
            flash(
                "Your password has been set. After you log in, you can "
                'go to the "Your Account" page to review your account '
                "information and settings.",
                "success",
            )
            return redirect(url_for("account.login"))
        return render_template("account/join_invite.html", form=form)
    else:
        flash(
            "The confirmation link is invalid or has expired. Another "
            "invite email with a new link has been sent to you.",
            "error",
        )
        token = new_user.generate_confirmation_token()
        invite_link = url_for(
            "account.join_from_invite", user_id=user_id, token=token, _external=True
        )
        send_email.delay(
            recipient=new_user.email,
            subject="You Are Invited To Join",
            template="account/email/invite",
            user=new_user,
            invite_link=invite_link,
        )
    return redirect(url_for(_ACCOUNT_MANAGE))


@account.before_app_request
def before_request():
    """Force user to confirm email before accessing login-required routes."""
    if (
        request.endpoint
        and current_user.is_authenticated
        and not current_user.confirmed
        and not request.endpoint.startswith("account")
        and request.endpoint != "static"
    ):
        return redirect(url_for("account.unconfirmed"))


@account.before_app_request
def check_username_status():
    """Force user to confirm email before accessing login-required routes."""
    if (
        request.endpoint
        and current_user.is_authenticated
        and not current_user.username
        and not request.endpoint.startswith("account")
        and request.endpoint != "static"
    ):
        flash("Please set up a username and profile data to continue", "warning")
        return redirect(url_for("account.change_username_request"))


@account.route("/unconfirmed")
def unconfirmed():
    """Catch users with unconfirmed emails."""
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for(_ACCOUNT_MANAGE))
    return render_template("socialite/account/unconfirmed.html")


@account.route("/settings")
@login_required
def fetch_settings():
    """ Allow fetching user settings."""
    setting = UserSetting.query.filter_by(user_id=current_user.id).first()
    return render_template("socialite/account/settings.html", setting=setting)


@account.route("/settings", methods=["POST"])
def create_account_settings():
    setting = UserSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
    form = request.form
    if request.method == "POST":
        if form.validate_on_submit():
            for field, value in form.data.items():
                if field == "csrf_token":
                    continue
                if field == "notification_interval":
                    setting.notification_interval = getattr(
                        NotificationIntervalEnum, field
                    ).value
                setattr(setting, field, value)
            db.session.add(setting)
            db.session.commit()
            flash("Settings Updated SuccessFully", "success")
        else:
            flash("Couldn't update Account settings", "error")
    return render_template("socialite/account/pages-setting.html", form=form)
