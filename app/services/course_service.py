from ..errors import AppError
from ..extensions import db
from ..models import Course


def create(staff, title, description, capacity):
    """Create a course owned by the given staff user (US4)."""
    course = Course(title=title, description=description, capacity=capacity, staff_id=staff.id)
    db.session.add(course)
    db.session.commit()
    return course


def update(staff, course_id, title, description, capacity):
    """Replace a course's details. Only its owner may do this."""
    course = _owned_course(staff, course_id)
    course.title = title
    course.description = description
    course.capacity = capacity
    db.session.commit()
    return course


def delete(staff, course_id):
    """Delete a course. Only its owner may do this."""
    course = _owned_course(staff, course_id)
    db.session.delete(course)
    db.session.commit()


def _owned_course(staff, course_id):
    """Return the course, or raise 404 if it does not exist and 403 if it is not yours."""
    course = db.session.get(Course, course_id)
    if course is None:
        raise AppError("NOT_FOUND", "Course not found.", 404)
    if course.staff_id != staff.id:
        raise AppError("FORBIDDEN", "You can only change your own courses.", 403)
    return course
