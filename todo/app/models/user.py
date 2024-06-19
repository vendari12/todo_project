from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from flask import current_app
from app import login_manager
from flask_login import  UserMixin,  AnonymousUserMixin
from sqlalchemy_utils import EmailType
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from .enums import UserRole
import logging

# Logger configuration
logger = logging.getLogger(__name__)

# Algorithm for JWT
_PASSWORD_ALGORITHM = "HS256"


@login_manager.user_loader
def load_user(user_id: int) -> Optional['User']:
    """Loads the user from the database using their ID."""
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)
    email = db.Column(EmailType, index=True, unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    tasks = db.relationship('Task', backref='author', lazy=True)
    confirmed = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"User('{self.username}')"

    @property
    def full_name(self) -> str:
        """Returns the full name of the user."""
        return f"{self.first_name} {self.last_name}"

    def can(self, permission: UserRole) -> bool:
        """Checks if the user has the given permission."""
        return self.role == permission or self.role == UserRole.ADMIN

    def is_admin(self) -> bool:
        """Checks if the user is an admin."""
        return self.can(UserRole.ADMIN)

    @property
    def password(self) -> None:
        """Raises an error when trying to access the password directly."""
        raise AttributeError("`password` is not a readable attribute")

    @password.setter
    def password(self, password: str) -> None:
        """Sets the password hash for the user."""
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password: str) -> bool:
        """Verifies the provided password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration: int = 604800) -> str:
        """Generates a token for email confirmation."""
        return self._generate_token('confirm', expiration)

    def generate_email_change_token(self, new_email: str, expiration: int = 3600) -> str:
        """Generates a token for changing the user's email."""
        return self._generate_token('change_email', expiration, new_email=new_email)

    def generate_password_reset_token(self, expiration: int = 3600) -> str:
        """Generates a token for resetting the user's password."""
        return self._generate_token('reset', expiration)

    def _generate_token(self, action: str, expiration: int, **extra_payload) -> str:
        """Helper method to generate JWT tokens with additional payload."""
        payload = {
            action: self.id,
            "exp": datetime.now(tz=timezone.utc) + timedelta(seconds=expiration),
            **extra_payload
        }
        token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=_PASSWORD_ALGORITHM)
        return token

    def confirm_account(self, token: str, expiration: int = 604800) -> bool:
        """Confirms the user's account using the provided token."""
        return self._verify_token(token, 'confirm', expiration)

    def change_email(self, token: str, expiration: int = 3600) -> bool:
        """Changes the user's email if the provided token is valid."""
        payload = self._verify_token(token, 'change_email', expiration, return_payload=True)
        if not payload:
            return False

        new_email = payload.get('new_email')
        if not new_email or User.query.filter_by(email=new_email).first():
            return False

        self.email = new_email
        db.session.commit()
        return True

    def reset_password(self, token: str, new_password: str, expiration: int = 3600) -> bool:
        """Resets the user's password if the provided token is valid."""
        if not self._verify_token(token, 'reset', expiration):
            return False
        self.password = new_password
        db.session.commit()
        return True

    def _verify_token(self, token: str, action: str, expiration: int, return_payload: bool = False) -> bool:
        """Helper method to verify JWT tokens."""
        try:
            payload = jwt.decode(
                token,
                current_app.config["SECRET_KEY"],
                leeway=timedelta(seconds=expiration),
                algorithms=[_PASSWORD_ALGORITHM]
            )
        except (InvalidTokenError, ExpiredSignatureError):
            logger.error(f"Invalid or expired token for {action}.")
            return False

        if payload.get(action) != self.id:
            logger.warning(f"Token action {action} mismatch for user ID {self.id}.")
            return False
        
        return payload if return_payload else True


    @staticmethod
    def generate_fake(count: int = 100, **kwargs) -> None:
        """Generates fake users for testing purposes."""
        from random import choice, seed, randint
        from faker import Faker
        from sqlalchemy.exc import IntegrityError

        fake = Faker()
        seed()
        roles = UserRole

        for _ in range(count):
            user = User(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                username=fake.user_name(),
                password="password",  # In real scenario, handle this securely
                confirmed=True,
                date_of_birth=f"{randint(1980, date.today().year - 18)}-{randint(1, 12)}-{randint(1, 31)}",
                role=choice([roles.USER, roles.ADMIN]),
                **kwargs,
            )
            db.session.add(user)
            try:
                db.session.commit()
                logger.info(f"Created user {user.full_name()}")
            except IntegrityError:
                db.session.rollback()
                continue

    @property
    def age(self) -> int:
        """Calculates the user's age from their date of birth."""
        try:
            dob_year, dob_month, dob_day = map(int, self.date_of_birth.split("-"))
            birth_date = date(dob_year, dob_month, dob_day)
            today = date.today()
            return today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
        except ValueError:
            logger.error(f"Error calculating age for user {self.username}. Invalid date format: {self.date_of_birth}")
            return 0


class AnonymousUser(AnonymousUserMixin):
    """Affords an overide for flask login anonymous user"""

    def can(self, _):
        return False

    def is_admin(self):
        return False


login_manager.anonymous_user = AnonymousUser