import os

import pytest
from dotenv import load_dotenv

from app import create_app
from app.extensions import db

load_dotenv()


@pytest.fixture(scope="session")
def app():
    """App wired to the skillboost_test database; tables are rebuilt once per run.

    No app context stays open during the tests. Each request then gets its own
    database session, as in production, so no test sees another test's stale data.
    """
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": os.environ["TEST_DATABASE_URL"],
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


def _empty_all_tables(app):
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture()
def client(app):
    """Test client. After each test, every table is emptied so tests stay independent."""
    yield app.test_client()
    _empty_all_tables(app)


@pytest.fixture()
def runner(app):
    """CLI test runner. After each test, every table is emptied."""
    yield app.test_cli_runner()
    _empty_all_tables(app)
