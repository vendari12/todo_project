from app.models.user import User
from flask_sqlalchemy import SQLAlchemy


def oauth_get_user_or_create(email: str, token: dict, db: SQLAlchemy) -> User:
    """Gets a user if exist or create a replica"""
    user_in_db = User.query.filter_by(email=email).first()
    if user_in_db:
        return user_in_db
    if token["email_verified"]:
        confirmed = True
    else:
        confirmed = False
    user_in_db = User(
        confirmed=confirmed,
        email=email,
        first_name=token["given_name"],
        last_name=token["family_name"],
    )
    db.session.add(user_in_db)
    db.session.commit()
    return user_in_db
