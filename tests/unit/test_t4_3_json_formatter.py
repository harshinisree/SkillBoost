import json
import logging
import sys

import pytest

from app import create_app
from app.logging_setup import JsonFormatter


def test_t4_3_formatter_writes_one_line_of_json_even_with_a_traceback():
    try:
        raise ValueError("line one\nline two")
    except ValueError:
        record = logging.LogRecord("skillboost", logging.ERROR, __file__, 1, "boom", None, None)
        record.exc_info = sys.exc_info()

    output = JsonFormatter().format(record)

    assert "\n" not in output
    entry = json.loads(output)
    assert entry["level"] == "ERROR"
    assert "ValueError" in entry["exception"]


@pytest.fixture()
def crashing_app():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": "unit-secret-0123456789abcdef"}
    )

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def test_t4_3_crash_is_logged_with_request_id_and_traceback(crashing_app, caplog):
    caplog.set_level(logging.INFO, logger="skillboost")

    response = crashing_app.test_client().get("/boom")

    [crash] = [r for r in caplog.records if r.name == "skillboost.errors"]
    entry = json.loads(JsonFormatter().format(crash))
    assert entry["request_id"] == response.headers["X-Request-ID"]
    assert "RuntimeError: kaboom" in entry["exception"]
