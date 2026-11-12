from flask import Blueprint, current_app, jsonify, request

from ..auth import create_access_token
from ..schemas import LoginSchema, RegisterSchema, validate_body
from ..services import user_service

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
def register():
    data = validate_body(RegisterSchema, request.get_json(silent=True))
    user = user_service.register(data.name, data.email, data.password, data.role)
    return jsonify(user.to_dict()), 201


@bp.post("/login")
def login():
    data = validate_body(LoginSchema, request.get_json(silent=True))
    user = user_service.login(data.email, data.password)
    return jsonify(
        {
            "access_token": create_access_token(user),
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_EXPIRES_SECONDS"],
        }
    ), 200
