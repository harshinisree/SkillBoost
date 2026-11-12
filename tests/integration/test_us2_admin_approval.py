import pytest

from app.extensions import db
from app.models import User
from app.services import user_service

PASSWORD = "StrongPass1"
ENDPOINTS = [("get", "/admin/pending"), ("post", "/admin/approve/1")]


def register(client, email, role="student"):
    response = client.post(
        "/auth/register",
        json={"name": "Test User", "email": email, "password": PASSWORD, "role": role},
    )
    return response.get_json()["id"]


def set_status(app, user_id, status):
    with app.app_context():
        db.session.get(User, user_id).status = status
        db.session.commit()


def status_of(app, user_id):
    with app.app_context():
        return db.session.get(User, user_id).status


def token(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": "Bearer " + response.get_json()["access_token"]}


@pytest.fixture()
def admin_headers(app, client):
    with app.app_context():
        user_service.create_admin("Admin User", "admin@example.com", PASSWORD)
    return token(client, "admin@example.com")


def test_us2_pending_list_shows_only_pending_users(app, client, admin_headers):
    register(client, "student@example.com", role="student")
    register(client, "staff@example.com", role="staff")
    approved_id = register(client, "approved@example.com")
    set_status(app, approved_id, "approved")

    response = client.get("/admin/pending", headers=admin_headers)

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert [item["email"] for item in items] == ["student@example.com", "staff@example.com"]


def test_us2_pending_list_shows_id_name_email_role_and_created_date(client, admin_headers):
    register(client, "student@example.com")

    [item] = client.get("/admin/pending", headers=admin_headers).get_json()["items"]

    assert set(item) >= {"id", "name", "email", "role", "created_at"}
    assert item["created_at"]
    assert "password" not in str(item)


def test_us2_approve_sets_status_approved_and_returns_200(app, client, admin_headers):
    user_id = register(client, "student@example.com")

    response = client.post(f"/admin/approve/{user_id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json()["status"] == "approved"
    assert status_of(app, user_id) == "approved"


@pytest.mark.parametrize("role", ["student", "staff"])
@pytest.mark.parametrize("method, path", ENDPOINTS)
def test_us2_non_admin_token_gets_403(app, client, role, method, path):
    user_id = register(client, f"{role}@example.com", role=role)
    set_status(app, user_id, "approved")

    response = getattr(client, method)(path, headers=token(client, f"{role}@example.com"))

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method, path", ENDPOINTS)
def test_us2_no_token_gets_401(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401


def test_us2_unknown_id_returns_404(client, admin_headers):
    response = client.post("/admin/approve/999999", headers=admin_headers)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_us2_approving_an_approved_user_returns_200_and_changes_nothing(
    app, client, admin_headers
):
    user_id = register(client, "student@example.com")
    first = client.post(f"/admin/approve/{user_id}", headers=admin_headers).get_json()

    second = client.post(f"/admin/approve/{user_id}", headers=admin_headers)

    assert second.status_code == 200
    assert second.get_json() == first
    assert status_of(app, user_id) == "approved"
