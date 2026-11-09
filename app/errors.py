from flask import jsonify


class AppError(Exception):
    """Raised by services; turned into the standard JSON error by the handler."""

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return error_response(err.code, err.message, err.status)

    @app.errorhandler(404)
    def handle_not_found(_err):
        return error_response("NOT_FOUND", "Resource not found.", 404)

    @app.errorhandler(500)
    def handle_internal_error(_err):
        return error_response("INTERNAL_ERROR", "Something went wrong.", 500)
