"""T4-1: errors raised by Flask itself, or by bugs, use the standard JSON shape.

A small throwaway app is used; no database is touched.
"""
import pytest

from app import create_app


@pytest.fixture()
def mini_client():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": "unit-secret-0123456789abcdef"}
    )

    @app.get("/boom")
    def boom():
        raise RuntimeError("database password is hunter2")

    return app.test_client()


def assert_standard_error(response, status, code):
    assert response.status_code == status
    assert response.is_json
    body = response.get_json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code


def test_t4_1_unknown_url_returns_json_404(mini_client):
    assert_standard_error(mini_client.get("/no-such-page"), 404, "NOT_FOUND")


def test_t4_1_non_numeric_id_in_url_returns_json_404(mini_client):
    assert_standard_error(mini_client.post("/admin/approve/abc"), 404, "NOT_FOUND")


def test_t4_1_wrong_method_returns_json_405_with_allow_header(mini_client):
    response = mini_client.post("/health")

    assert_standard_error(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["Allow"]


def test_t4_1_unexpected_crash_returns_json_500_without_details(mini_client):
    response = mini_client.get("/boom")

    assert_standard_error(response, 500, "INTERNAL_ERROR")
    text = response.get_data(as_text=True)
    assert "hunter2" not in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text
