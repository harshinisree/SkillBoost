import itertools
import os

import pytest
from dotenv import load_dotenv
from flask import Blueprint, g, jsonify

from app import create_app
from app.auth import role_required, token_required
from app.extensions import db
from app.services import user_service

load_dotenv()

TEST_JWT_SECRET = "test-secret-only-for-pytest-0123456789abcdef"


def _add_test_only_routes(app):
    """Protected routes that exist only during tests, to exercise the decorators."""
    bp = Blueprint("test_only", __name__)

    @bp.get("/_test/protected")
    @token_required
    def protected():
        return jsonify({"user_id": g.current_user.id, "role": g.current_user.role})

    @bp.get("/_test/staff-only")
    @role_required("staff")
    def staff_only():
        return jsonify({"ok": True})

    app.register_blueprint(bp)


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
            "JWT_SECRET": TEST_JWT_SECRET,
        }
    )
    _add_test_only_routes(app)
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


@pytest.fixture()
def make_user(app, client):
    """Create an approved user and log them in.

    Usage:  user_id, headers = make_user("staff")
    headers is ready to pass to client.get/post/put/delete.
    """
    counter = itertools.count(1)

    def _make(role="student", email=None, password="StrongPass1"):
        email = email or f"{role}{next(counter)}@example.com"
        with app.app_context():
            if role == "admin":
                user = user_service.create_admin("Test Admin", email, password)
            else:
                user = user_service.register("Test User", email, password, role)
                user.status = "approved"
                db.session.commit()
            user_id = user.id
        response = client.post("/auth/login", json={"email": email, "password": password})
        return user_id, {"Authorization": "Bearer " + response.get_json()["access_token"]}

    return _make
