from flask import jsonify
from werkzeug.exceptions import HTTPException, MethodNotAllowed


class AppError(Exception):
    """Raised by services; turned into the standard JSON error by the handler."""

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


# Friendlier wording for the HTTP errors people actually hit.
HTTP_MESSAGES = {
    404: "Resource not found.",
    405: "This method is not allowed for this URL.",
}


def register_error_handlers(app):
    """Every error leaves the API in one shape: {"error": {"code": ..., "message": ...}}."""

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return error_response(err.code, err.message, err.status)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        # Werkzeug's own errors (404 unknown URL, 405 wrong method, ...) as JSON.
        code = err.name.upper().replace(" ", "_")
        message = HTTP_MESSAGES.get(err.code, f"{err.name}.")
        response, status = error_response(code, message, err.code)
        if isinstance(err, MethodNotAllowed) and err.valid_methods:
            response.headers["Allow"] = ", ".join(sorted(err.valid_methods))
        return response, status

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        # The full traceback goes to the server log, never to the client.
        app.logger.exception("Unhandled error")
        return error_response("INTERNAL_ERROR", "Something went wrong.", 500)
