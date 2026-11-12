import jwt
import pytest

from app.auth import create_access_token
from app.extensions import db
from app.models import User

PASSWORD = "StrongPass1"


def make_user(app, client, email="asha@example.com", role="student", status="approved"):
    """Register through the API, then set the status directly (US2 approval comes later)."""
    client.post(
        "/auth/register",
        json={"name": "Asha Rao", "email": email, "password": PASSWORD, "role": role},
    )
    with app.app_context():
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one()
        user.status = status
        db.session.commit()
        return user.id


def login(client, email="asha@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_us3_approved_user_gets_200_with_token(app, client):
    make_user(app, client)

    response = login(client)

    assert response.status_code == 200
    body = response.get_json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]


def test_us3_token_carries_user_id_role_and_expiry(app, client):
    user_id = make_user(app, client, role="staff")

    token = login(client).get_json()["access_token"]

    claims = jwt.decode(token, app.config["JWT_SECRET"], algorithms=["HS256"])
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "staff"
    assert claims["exp"] - claims["iat"] == 3600


def test_us3_wrong_password_and_unknown_email_give_the_same_401(app, client):
    make_user(app, client)

    wrong_password = login(client, password="WrongPass99")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


def test_us3_pending_account_returns_403(app, client):
    make_user(app, client, status="pending")

    response = login(client)

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_us3_pending_account_with_wrong_password_returns_401_not_403(app, client):
    make_user(app, client, status="pending")

    response = login(client, password="WrongPass99")

    assert response.status_code == 401


def test_us3_login_email_ignores_letter_case(app, client):
    make_user(app, client)

    response = login(client, email="ASHA@Example.com")

    assert response.status_code == 200


@pytest.mark.parametrize("missing", ["email", "password"])
def test_us3_missing_field_returns_400(client, missing):
    payload = {"email": "asha@example.com", "password": PASSWORD}
    del payload[missing]

    response = client.post("/auth/login", json=payload)

    assert response.status_code == 400
    assert missing in response.get_json()["error"]["message"]


def test_us3_token_from_login_opens_a_protected_route(app, client):
    user_id = make_user(app, client)
    token = login(client).get_json()["access_token"]

    response = client.get("/_test/protected", headers=bearer(token))

    assert response.status_code == 200
    assert response.get_json() == {"user_id": user_id, "role": "student"}


def test_us3_expired_token_returns_401_on_a_protected_route(app, client):
    user_id = make_user(app, client)
    with app.app_context():
        token = create_access_token(db.session.get(User, user_id), expires_in=-10)

    response = client.get("/_test/protected", headers=bearer(token))

    assert response.status_code == 401


def test_us3_tampered_token_returns_401_on_a_protected_route(app, client):
    make_user(app, client)
    token = login(client).get_json()["access_token"]
    header, payload, signature = token.split(".")
    tampered = ".".join([header, payload, signature[:-4] + "AAAA"])

    response = client.get("/_test/protected", headers=bearer(tampered))

    assert response.status_code == 401


@pytest.mark.parametrize("header", [{}, {"Authorization": "Token abc"}, {"Authorization": "Bearer"}])
def test_us3_missing_or_malformed_header_returns_401(client, header):
    response = client.get("/_test/protected", headers=header)

    assert response.status_code == 401


def test_us3_role_required_blocks_wrong_role_and_allows_right_one(app, client):
    make_user(app, client, email="student@example.com", role="student")
    make_user(app, client, email="staff@example.com", role="staff")
    student_token = login(client, email="student@example.com").get_json()["access_token"]
    staff_token = login(client, email="staff@example.com").get_json()["access_token"]

    assert client.get("/_test/staff-only", headers=bearer(student_token)).status_code == 403
    assert client.get("/_test/staff-only", headers=bearer(staff_token)).status_code == 200
