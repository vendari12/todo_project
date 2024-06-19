import pytest
from app import db
from app.models import User
from tests.fixtures.user import SAMPLE_USER_DATA_2


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

@pytest.fixture()
def mock_current_user_object(mocker):
    user = User(**SAMPLE_USER_DATA_2)
    db.session.add(user)
    db.session.commit()
    return mocker.path('flask_login.utils._get_user', return_value=user)