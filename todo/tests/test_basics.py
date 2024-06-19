import unittest

from app import create_app, db
from app.models import User
from flask import current_app
from flask.testing import FlaskClient
from flask_login import FlaskLoginClient


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.base_url = "http://localhost:5000"
        self.app.test_client_class = FlaskLoginClient
        self.client: FlaskClient = self.app.test_client()
        self.json_headers = {"Content-Type": "application/json"}
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertIsNot(current_app, None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config["TESTING"])

    def create_user(self, **kwargs):
        user = User(**kwargs)
        db.session.add(user)
        db.session.commit()
        return user
