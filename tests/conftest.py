import os

import pytest
from dotenv import load_dotenv

from app import create_app
from app.extensions import db

load_dotenv()


@pytest.fixture(scope="session")
def app():
    """App wired to the skillboost_test database; tables created once per run."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": os.environ["TEST_DATABASE_URL"],
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
