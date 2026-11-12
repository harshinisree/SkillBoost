"""End-to-end: a new user cannot log in until an admin approves them."""
from app.services import user_service

PASSWORD = "StrongPass1"


def login(client, email):
    return client.post("/auth/login", json={"email": email, "password": PASSWORD})


def test_us2_full_flow_register_wait_approve_login(app, client):
    with app.app_context():
        user_service.create_admin("Admin User", "admin@example.com", PASSWORD)
    admin = {"Authorization": "Bearer " + login(client, "admin@example.com").get_json()["access_token"]}

    # 1. A student registers and is pending.
    registered = client.post(
        "/auth/register",
        json={"name": "Asha Rao", "email": "asha@example.com", "password": PASSWORD, "role": "student"},
    ).get_json()
    assert registered["status"] == "pending"

    # 2. Before approval, login is refused with 403.
    assert login(client, "asha@example.com").status_code == 403

    # 3. The admin sees the student in the pending list and approves them.
    pending = client.get("/admin/pending", headers=admin).get_json()["items"]
    assert [item["email"] for item in pending] == ["asha@example.com"]
    approved = client.post(f"/admin/approve/{registered['id']}", headers=admin)
    assert approved.status_code == 200

    # 4. Now login works, and the pending list is empty.
    assert login(client, "asha@example.com").status_code == 200
    assert client.get("/admin/pending", headers=admin).get_json()["items"] == []
