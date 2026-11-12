from flask import Blueprint, g, jsonify, request

from ..auth import role_required, token_required
from ..schemas import CourseListQuery, CourseSchema, validate_body
from ..services import course_service

bp = Blueprint("courses", __name__, url_prefix="/courses")


@bp.get("")
@token_required
def list_courses():
    params = validate_body(CourseListQuery, request.args.to_dict())
    items, total, page, per_page = course_service.list_courses(
        params.page, params.per_page, params.q, params.sort
    )
    return jsonify(
        {
            "items": [course.to_dict() for course in items],
            "page": page,
            "per_page": per_page,
            "total": total,
        }
    ), 200


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
