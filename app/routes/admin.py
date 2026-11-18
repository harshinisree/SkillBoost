from flask import Blueprint, g, jsonify
from flask.typing import ResponseReturnValue

from ..auth import role_required
from ..services import user_service

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/pending")
@role_required("admin")
def pending() -> ResponseReturnValue:
    users = user_service.list_pending()
    return jsonify({"items": [user.to_dict() for user in users]}), 200


@bp.post("/approve/<int:user_id>")
@role_required("admin")
def approve(user_id: int) -> ResponseReturnValue:
    user = user_service.approve(user_id, g.current_user)
    return jsonify(user.to_dict()), 200
