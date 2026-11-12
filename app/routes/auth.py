from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from ..auth import create_access_token
from ..errors import AppError
from ..schemas import LoginSchema, RegisterSchema
from ..services import user_service

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _validated(schema, payload):
    """Validate a JSON body against a schema, or raise a 400 naming the bad fields."""
    if not isinstance(payload, dict):
        raise AppError("VALIDATION_ERROR", "Request body must be a JSON object.", 400)
    try:
        return schema.model_validate(payload)
    except ValidationError as err:
        fields = list(dict.fromkeys(str(e["loc"][0]) for e in err.errors() if e["loc"]))
        message = "Invalid or missing field(s): " + ", ".join(fields) + "."
        raise AppError("VALIDATION_ERROR", message, 400) from err


@bp.post("/register")
def register():
    data = _validated(RegisterSchema, request.get_json(silent=True))
    user = user_service.register(data.name, data.email, data.password, data.role)
    return jsonify(user.to_dict()), 201


@bp.post("/login")
def login():
    data = _validated(LoginSchema, request.get_json(silent=True))
    user = user_service.login(data.email, data.password)
    return jsonify(
        {
            "access_token": create_access_token(user),
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_EXPIRES_SECONDS"],
        }
    ), 200
