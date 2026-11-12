from flask import Blueprint, g, jsonify, request

from ..auth import role_required
from ..schemas import EnrollSchema, validate_body
from ..services import enrollment_service

bp = Blueprint("enrollments", __name__, url_prefix="/enrollments")


@bp.post("")
@role_required("student")
def enroll():
    data = validate_body(EnrollSchema, request.get_json(silent=True))
    enrollment = enrollment_service.enroll(g.current_user, data.course_id)
    return jsonify(enrollment.to_dict()), 201


@bp.delete("/<int:course_id>")
@role_required("student")
def drop(course_id):
    enrollment_service.drop(g.current_user, course_id)
    return "", 204
