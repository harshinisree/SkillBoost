"""T4-3: one JSON log line per request, with a request ID; no secrets in logs."""
import json
import logging
import re

import pytest

from app.logging_setup import JsonFormatter

FORMAT = JsonFormatter()


@pytest.fixture()
def request_logs(caplog):
    """Returns a function giving the request log lines so far, parsed from JSON."""
    caplog.set_level(logging.INFO, logger="skillboost")

    def _lines():
        return [json.loads(FORMAT.format(r)) for r in caplog.records if r.name == "skillboost.request"]

    return _lines


def test_t4_3_each_request_writes_one_json_line(client, request_logs):
    client.get("/health")

    [line] = request_logs()
    assert line["level"] == "INFO"
    assert (line["method"], line["path"], line["status"]) == ("GET", "/health", 200)
    assert line["duration_ms"] >= 0
    assert line["timestamp"].endswith("+00:00")
    assert line["request_id"]


def test_t4_3_response_carries_the_same_request_id_as_the_log(client, request_logs):
    response = client.get("/health")

    [line] = request_logs()
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])
    assert line["request_id"] == response.headers["X-Request-ID"]


def test_t4_3_incoming_request_id_is_reused(client, request_logs):
    response = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})

    assert response.headers["X-Request-ID"] == "trace-abc-123"
    assert request_logs()[0]["request_id"] == "trace-abc-123"


@pytest.mark.parametrize("unsafe", ["has spaces", "x" * 65, "<script>", "line\\nbreak"])
def test_t4_3_unsafe_incoming_request_id_is_replaced(client, unsafe):
    response = client.get("/health", headers={"X-Request-ID": unsafe})

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Request-ID"])


def test_t4_3_error_responses_are_logged_with_their_status(client, request_logs):
    client.get("/no-such-page")

    assert request_logs()[0]["status"] == 404


def test_t4_3_logged_in_user_id_is_logged(client, make_user, request_logs):
    user_id, headers = make_user("student")
    client.get("/enrollments/me", headers=headers)

    line = request_logs()[-1]
    assert line["path"] == "/enrollments/me"
    assert line["user_id"] == user_id


def test_t4_3_anonymous_requests_have_no_user_id(client, request_logs):
    client.get("/health")

    assert "user_id" not in request_logs()[0]


def test_t4_3_passwords_and_tokens_never_reach_the_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    password = "SuperSecretPass42"
    client.post(
        "/auth/register",
        json={"name": "Asha Rao", "email": "asha@example.com", "password": password, "role": "student"},
    )
    client.post("/auth/login", json={"email": "asha@example.com", "password": password})
    token = "eyJhbGciOiJIUzI1NiJ9.fake-but-token-shaped.signature"
    client.get("/courses", headers={"Authorization": f"Bearer {token}"})

    everything = caplog.text + "".join(FORMAT.format(r) for r in caplog.records)
    assert password not in everything
    assert token not in everything
    assert "Bearer" not in everything
