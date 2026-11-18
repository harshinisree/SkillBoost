"""T4-8: routine health checks stay out of the log, but problems never do."""
import json
import logging

import pytest

from app.logging_setup import JsonFormatter


@pytest.fixture()
def request_lines(caplog):
    caplog.set_level(logging.INFO, logger="skillboost")

    def _lines():
        return [json.loads(JsonFormatter().format(r)) for r in caplog.records if r.name == "skillboost.request"]

    return _lines


def test_t4_8_successful_health_checks_are_not_logged(client, request_lines):
    for _ in range(3):
        assert client.get("/health").status_code == 200

    assert request_lines() == []


def test_t4_8_health_checks_still_get_a_request_id(client):
    assert client.get("/health").headers["X-Request-ID"]


def test_t4_8_a_failing_health_request_is_still_logged(client, request_lines):
    client.post("/health")  # wrong method: 405

    [line] = request_lines()
    assert (line["path"], line["status"]) == ("/health", 405)


def test_t4_8_other_requests_are_still_logged(client, request_lines):
    client.get("/health")
    client.get("/openapi.json")

    assert [line["path"] for line in request_lines()] == ["/openapi.json"]
