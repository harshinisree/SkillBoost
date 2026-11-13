"""Structured logging: one JSON line per log record, tagged with a request ID.

Every request gets an ID (reused from an incoming X-Request-ID header if it is
safe, otherwise generated). The ID is returned in the X-Request-ID response
header and added to every log line written while handling that request, so a
user's error report can be matched to the exact server log lines.

Only the method, path, status, timing, and user id are logged. Request bodies,
headers, and query strings are never logged, so passwords and tokens cannot leak.
"""
import json
import logging
import re
import sys
import time
import uuid
from datetime import UTC, datetime

from flask import g, has_request_context, request

LOGGER_NAME = "skillboost"
REQUEST_FIELDS = ("request_id", "method", "path", "status", "duration_ms", "user_id")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

request_log = logging.getLogger(f"{LOGGER_NAME}.request")


class JsonFormatter(logging.Formatter):
    """Format a log record as a single line of JSON."""

    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in REQUEST_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


class RequestIdFilter(logging.Filter):
    """Add the current request's ID to every record logged during that request."""

    def filter(self, record):
        if getattr(record, "request_id", None) is None and has_request_context():
            record.request_id = g.get("request_id")
        return True


def configure_logging(app):
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(app.config["LOG_LEVEL"])
    if not logger.handlers:  # create_app can run many times (tests); add one handler only
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    @app.before_request
    def start_request():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.request_id
        request_log.info(
            "request",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - g.request_started) * 1000, 1),
                "user_id": g.get("user_id"),
            },
        )
        return response
