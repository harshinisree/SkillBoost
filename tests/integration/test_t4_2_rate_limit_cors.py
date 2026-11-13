"""T4-2: login is rate-limited per client, and only listed origins get CORS access."""
import pytest

from app.extensions import db, limiter
from app.services import user_service

PASSWORD = "StrongPass1"
ALLOWED = "https://frontend.example"  # set in conftest as the only CORS origin


@pytest.fixture()
def user_email(app, client):
    """An approved user created directly, without logging in."""
    with app.app_context():
        user = user_service.register("Asha Rao", "asha@example.com", PASSWORD, "student")
        user.status = "approved"
        db.session.commit()
    return "asha@example.com"


@pytest.fixture()
def real_login_limit(app):
    """Switch the test app to the production limit for one test, with fresh counters."""
    original = app.config["LOGIN_RATE_LIMIT"]
    app.config["LOGIN_RATE_LIMIT"] = "5 per minute"
    with app.app_context():
        limiter.reset()
    yield
    app.config["LOGIN_RATE_LIMIT"] = original
    with app.app_context():
        limiter.reset()


def login(client, email, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------- rate limit ----------

def test_t4_2_sixth_login_in_a_minute_returns_429(client, user_email, real_login_limit):
    statuses = [login(client, user_email).status_code for _ in range(6)]

    assert statuses == [200, 200, 200, 200, 200, 429]


def test_t4_2_429_uses_the_standard_error_format_and_says_when_to_retry(
    client, user_email, real_login_limit
):
    for _ in range(5):
        login(client, user_email)

    response = login(client, user_email)

    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert int(response.headers["Retry-After"]) > 0


def test_t4_2_failed_guesses_count_toward_the_limit(client, user_email, real_login_limit):
    wrong = [login(client, user_email, "WrongGuess9").status_code for _ in range(5)]

    right = login(client, user_email)

    assert wrong == [401] * 5
    assert right.status_code == 429  # even the correct password waits


def test_t4_2_limit_applies_only_to_login(client, user_email, real_login_limit):
    for _ in range(6):
        login(client, user_email)

    assert client.get("/health").status_code == 200
    register = client.post(
        "/auth/register",
        json={"name": "New Person", "email": "new@example.com", "password": PASSWORD, "role": "student"},
    )
    assert register.status_code == 201


# ---------- CORS ----------

def test_t4_2_allowed_origin_gets_cors_header(client):
    response = client.get("/health", headers={"Origin": ALLOWED})

    assert response.headers.get("Access-Control-Allow-Origin") == ALLOWED


def test_t4_2_unlisted_origin_gets_no_cors_header(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "Access-Control-Allow-Origin" not in response.headers


def test_t4_2_preflight_from_allowed_origin_permits_json_with_a_token(client):
    response = client.options(
        "/courses",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == ALLOWED
    allowed_headers = response.headers.get("Access-Control-Allow-Headers", "").lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
