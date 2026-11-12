import bcrypt
import pytest

from app.extensions import db
from app.models import User

VALID = {
    "name": "Asha Rao",
    "email": "asha@example.com",
    "password": "StrongPass1",
    "role": "student",
}


def register(client, **overrides):
    return client.post("/auth/register", json={**VALID, **overrides})


def stored_user(app, email):
    """Read the user row in a fresh app context, so MySQL shows the latest commit."""
    with app.app_context():
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user is None:
            return None
        return {"status": user.status, "role": user.role, "password_hash": user.password_hash}


@pytest.mark.parametrize("role", ["student", "staff"])
def test_us1_register_valid_input_returns_201_and_pending(client, role):
    response = register(client, role=role)

    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Asha Rao"
    assert body["email"] == "asha@example.com"
    assert body["role"] == role
    assert body["status"] == "pending"
    assert isinstance(body["id"], int)


def test_us1_register_response_never_contains_the_password(client):
    response = register(client)

    assert response.status_code == 201
    text = response.get_data(as_text=True)
    assert "password" not in text
    assert "StrongPass1" not in text


def test_us1_register_stores_a_bcrypt_hash_not_the_password(client, app):
    register(client)

    row = stored_user(app, "asha@example.com")
    assert row["password_hash"] != "StrongPass1"
    assert row["password_hash"].startswith("$2")
    assert bcrypt.checkpw(b"StrongPass1", row["password_hash"].encode("utf-8"))


def test_us1_register_new_account_is_pending_in_the_database(client, app):
    register(client)

    assert stored_user(app, "asha@example.com")["status"] == "pending"


def test_us1_register_duplicate_email_returns_409_email_taken(client):
    register(client)

    response = register(client, name="Someone Else")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "EMAIL_TAKEN"


def test_us1_register_duplicate_email_ignores_letter_case(client):
    register(client)

    response = register(client, email="ASHA@Example.com")

    assert response.status_code == 409


@pytest.mark.parametrize("field", ["name", "email", "password", "role"])
def test_us1_register_missing_field_returns_400_naming_the_field(client, field):
    payload = {k: v for k, v in VALID.items() if k != field}

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["message"]


def test_us1_register_invalid_email_returns_400(client):
    response = register(client, email="not-an-email")

    assert response.status_code == 400
    assert "email" in response.get_json()["error"]["message"]


def test_us1_register_short_password_returns_400(client):
    response = register(client, password="short")

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]["message"]


def test_us1_register_admin_role_is_rejected_with_400(client, app):
    response = register(client, role="admin")

    assert response.status_code == 400
    assert "role" in response.get_json()["error"]["message"]
    assert stored_user(app, "asha@example.com") is None


def test_us1_register_body_that_is_not_json_returns_400(client):
    response = client.post("/auth/register", data="this is not json")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"
