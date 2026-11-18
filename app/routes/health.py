from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

bp = Blueprint("health", __name__)


@bp.get("/health")
def health() -> ResponseReturnValue:
    return jsonify({"status": "ok"})
