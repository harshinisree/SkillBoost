"""Unit tests for the JWT helpers and the two decorators.

No real database: the user lookup is replaced with a fake, and a small
throwaway app is built for each test.
"""
from datetime import UTC, datetime
from types import SimpleNamespace

import jwt
import pytest
from flask import Blueprint, jsonify

from app import auth, create_app
from app.errors import AppError

SECRET = "unit-test-secret-0123456789abcdef0123456789"
STAFF = SimpleNamespace(id=7, role="staff", status="approved")


@pytest.fixture()
def mini_app(monkeypatch):
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": SECRET}
    )
    bp = Blueprint("unit_routes", __name__)

    @bp.get("/protected")
    @auth.token_required
    def protected():
        return jsonify({"ok": True})

    @bp.get("/admin-only")
    @auth.role_required("admin")
    def admin_only():
        return jsonify({"ok": True})

    app.register_blueprint(bp)
    monkeypatch.setattr(auth, "_load_user", lambda user_id: STAFF if user_id == 7 else None)
    return app


def token_for(app, user, **kwargs):
    with app.app_context():
        return auth.create_access_token(user, **kwargs)


def test_us3_token_carries_user_id_role_and_one_hour_expiry(mini_app):
    claims = jwt.decode(token_for(mini_app, STAFF), SECRET, algorithms=["HS256"])

    assert claims["sub"] == "7"
    assert claims["role"] == "staff"
    assert claims["exp"] - claims["iat"] == 3600


def test_us3_expired_token_is_rejected_with_401(mini_app):
    token = token_for(mini_app, STAFF, expires_in=-10)

    with mini_app.app_context(), pytest.raises(AppError) as err:
        auth.decode_access_token(token)
    assert err.value.status == 401
    assert "expired" in err.value.message


def test_us3_tampered_token_is_rejected_with_401(mini_app):
    token = token_for(mini_app, STAFF)
    header, _payload, signature = token.split(".")
    forged = jwt.encode(
        {"sub": "7", "role": "admin", "exp": datetime(2099, 1, 1, tzinfo=UTC)},
        "attacker-secret-0123456789abcdef0123456789",
        algorithm="HS256",
    )
    tampered = ".".join([header, forged.split(".")[1], signature])

    with mini_app.app_context(), pytest.raises(AppError) as err:
        auth.decode_access_token(tampered)
    assert err.value.status == 401


def test_us3_missing_secret_fails_loudly():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": None})

    with app.app_context(), pytest.raises(RuntimeError):
        auth.create_access_token(STAFF)


def test_us3_token_required_allows_a_valid_token(mini_app):
    token = token_for(mini_app, STAFF)

    response = mini_app.test_client().get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer ", "Token abc", "abc"])
def test_us3_token_required_rejects_missing_or_malformed_header(mini_app, header):
    headers = {} if header is None else {"Authorization": header}

    response = mini_app.test_client().get("/protected", headers=headers)

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_us3_token_required_rejects_token_for_unknown_user(mini_app):
    token = token_for(mini_app, SimpleNamespace(id=999, role="staff"))

    response = mini_app.test_client().get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_us3_role_required_blocks_the_wrong_role_with_403(mini_app):
    token = token_for(mini_app, STAFF)

    response = mini_app.test_client().get(
        "/admin-only", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_us3_role_required_without_token_returns_401(mini_app):
    response = mini_app.test_client().get("/admin-only")

    assert response.status_code == 401
