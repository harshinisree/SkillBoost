"""T4-1: one test per error code, through real endpoints, all in the standard shape."""
import pytest

STUDENT = {"name": "Asha Rao", "email": "asha@example.com", "password": "StrongPass1", "role": "student"}


def assert_standard_error(response, status, code):
    assert response.status_code == status
    assert response.is_json
    body = response.get_json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_t4_1_400_validation_error(client):
    response = client.post("/auth/register", json={**STUDENT, "email": "not-an-email"})

    assert_standard_error(response, 400, "VALIDATION_ERROR")


def test_t4_1_401_unauthorized(client):
    assert_standard_error(client.get("/courses"), 401, "UNAUTHORIZED")


def test_t4_1_403_forbidden(client, make_user):
    _, student = make_user("student")

    response = client.post("/courses", json={"title": "X", "capacity": 5}, headers=student)

    assert_standard_error(response, 403, "FORBIDDEN")


def test_t4_1_404_not_found(client, make_user):
    _, student = make_user("student")

    response = client.post("/enrollments", json={"course_id": 999999}, headers=student)

    assert_standard_error(response, 404, "NOT_FOUND")


def test_t4_1_405_method_not_allowed(client):
    assert_standard_error(client.get("/auth/login"), 405, "METHOD_NOT_ALLOWED")


def test_t4_1_409_conflict(client):
    client.post("/auth/register", json=STUDENT)

    response = client.post("/auth/register", json=STUDENT)

    assert_standard_error(response, 409, "EMAIL_TAKEN")


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/admin/pending"),
        ("post", "/admin/approve/1"),
        ("get", "/courses"),
        ("post", "/courses"),
        ("put", "/courses/1"),
        ("delete", "/courses/1"),
        ("post", "/enrollments"),
        ("delete", "/enrollments/1"),
        ("get", "/enrollments/me"),
    ],
)
def test_t4_1_every_protected_endpoint_rejects_missing_token_as_json(client, method, path):
    assert_standard_error(getattr(client, method)(path), 401, "UNAUTHORIZED")
