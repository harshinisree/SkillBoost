from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from ..errors import AppError
from ..schemas import RegisterSchema
from ..services import user_service

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
def register():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AppError("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    try:
        data = RegisterSchema.model_validate(payload)
    except ValidationError as err:
        fields = list(dict.fromkeys(str(e["loc"][0]) for e in err.errors() if e["loc"]))
        message = "Invalid or missing field(s): " + ", ".join(fields) + "."
        raise AppError("VALIDATION_ERROR", message, 400) from err

    user = user_service.register(data.name, data.email, data.password, data.role)
    return jsonify(user.to_dict()), 201
