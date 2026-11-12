from flask import Blueprint, g, jsonify, request

from ..auth import role_required
from ..schemas import CourseSchema, validate_body
from ..services import course_service

bp = Blueprint("courses", __name__, url_prefix="/courses")


@bp.post("")
@role_required("staff")
def create_course():
    data = validate_body(CourseSchema, request.get_json(silent=True))
    course = course_service.create(g.current_user, data.title, data.description, data.capacity)
    return jsonify(course.to_dict()), 201


@bp.put("/<int:course_id>")
@role_required("staff")
def update_course(course_id):
    data = validate_body(CourseSchema, request.get_json(silent=True))
    course = course_service.update(
        g.current_user, course_id, data.title, data.description, data.capacity
    )
    return jsonify(course.to_dict()), 200


@bp.delete("/<int:course_id>")
@role_required("staff")
def delete_course(course_id):
    course_service.delete(g.current_user, course_id)
    return "", 204
