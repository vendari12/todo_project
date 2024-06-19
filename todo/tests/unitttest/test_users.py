import time
from http import HTTPStatus
import faker
import pytest
from app import db
from app.models.user import AnonymousUser, UserRole, User
from flask import request
from flask.testing import FlaskClient
from tests.fixtures.user import SAMPLE_USER_DATA

from tests.test_basics import BasicsTestCase

fake_generator = faker.Faker()


class UserModelTestCase(BasicsTestCase):
    def test_password_setter(self):
        u = User(password="password")
        self.assertIsNot(u.password_hash, None)

    def test_no_password_getter(self):
        u = User(password="password")
        with self.assertRaises(AttributeError):
            u.password()

    def test_password_verification(self):
        u = User(password="password")
        self.assertTrue(u.verify_password("password"))
        self.assertFalse(u.verify_password("notpassword"))

    def test_password_salts_are_random(self):
        u = User(password="password")
        u2 = User(password="password")
        self.assertNotEqual(u.password_hash, u2.password_hash)

    def test_valid_confirmation_token(self):
        u = User(
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm_account(token))

    def test_invalid_confirmation_token(self):
        u1 = User(
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        u2 = User(
            password="notpassword",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm_account(token))

    def test_expired_confirmation_token(self):
        u = User(
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token(expiration=10)
        time.sleep(20)
        self.assertFalse(u.confirm_account(token, expiration=10))

    def test_valid_reset_token(self):
        u = User(
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u)
        db.session.commit()
        token = u.generate_password_reset_token()
        self.assertTrue(u.reset_password(token, "notpassword"))
        self.assertTrue(u.verify_password("notpassword"))

    def test_invalid_reset_token(self):
        u1 = User(
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        u2 = User(
            password="notpassword",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            email=fake_generator.email(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_password_reset_token()
        self.assertFalse(u2.reset_password(token, "notnotpassword"))
        self.assertTrue(u2.verify_password("notpassword"))

    def test_valid_email_change_token(self):
        u = User(
            email="user@example.com",
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u)
        db.session.commit()
        token = u.generate_email_change_token("otheruser@example.org")
        self.assertTrue(u.change_email(token))
        self.assertEqual(u.email, "otheruser@example.org")

    def test_invalid_email_change_token(self):
        u1 = User(
            email="user@example.com",
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        u2 = User(
            email="otheruser@example.org",
            password="notpassword",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_email_change_token("otherotheruser@example.net")
        self.assertFalse(u2.change_email(token))
        self.assertEqual(u2.email, "otheruser@example.org")

    def test_duplicate_email_change_token(self):
        u1 = User(
            email="user@example.com",
            password="password",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        u2 = User(
            email="otheruser@example.org",
            password="notpassword",
            first_name=fake_generator.first_name(),
            last_name=fake_generator.last_name(),
            username=fake_generator.user_name(),
            date_of_birth="2008-01-15",
        )
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u2.generate_email_change_token("user@example.com")
        self.assertFalse(u2.change_email(token))
        self.assertEqual(u2.email, "otheruser@example.org")

    def test_user_role_and_admin_roles_permissions(self):
        u = User(email="user@example.com", password="password", role=UserRole.USER)
        self.assertFalse(u.can(UserRole.ADMIN))
        self.assertTrue(u.can(UserRole.USER))

    def test_make_administrator(self):
        u = User(email="user@example.com", password="password")
        self.assertFalse(u.can(UserRole.ADMIN))
        u.role = UserRole.ADMIN
        self.assertTrue(u.can(UserRole.ADMIN))

    def test_administrator(self):
        u = User(email="user@example.com", password="password", role=UserRole.ADMIN)
        self.assertTrue(u.can(UserRole.ADMIN))
        self.assertTrue(u.can(UserRole.USER))
        self.assertTrue(u.is_admin())

    def test_anonymous(self):
        u = AnonymousUser()
        self.assertFalse(u.can(UserRole.USER))
