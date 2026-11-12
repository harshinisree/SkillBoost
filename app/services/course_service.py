from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import Course, Enrollment

MAX_PER_PAGE = 100

# Each sort also orders by id, so rows with the same title or timestamp
# keep a fixed order and never jump between pages.
SORTS = {
    "title": (Course.title.asc(), Course.id.asc()),
    "-title": (Course.title.desc(), Course.id.desc()),
    "created_at": (Course.created_at.asc(), Course.id.asc()),
    "-created_at": (Course.created_at.desc(), Course.id.desc()),
}


def list_courses(page=1, per_page=20, q="", sort="-created_at"):
    """One page of courses, optionally filtered by title (US5).

    Returns (items, total, page, per_page). per_page is capped at MAX_PER_PAGE.
    """
    per_page = min(per_page, MAX_PER_PAGE)
    query = db.select(Course)
    if q:
        # autoescape makes % and _ in the search text match literally.
        query = query.where(func.lower(Course.title).contains(q.lower(), autoescape=True))

    total = db.session.execute(
        db.select(func.count()).select_from(query.subquery())
    ).scalar_one()
    items = db.session.execute(
        query.order_by(*SORTS[sort]).limit(per_page).offset((page - 1) * per_page)
    ).scalars().all()
    return items, total, page, per_page


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
    """Delete a course. Only its owner may do this, and only while nobody is enrolled."""
    course = _owned_course(staff, course_id)
    has_students = db.session.execute(
        db.select(Enrollment.id).filter_by(course_id=course.id).limit(1)
    ).first()
    if has_students:
        raise _has_enrollments()
    db.session.delete(course)
    try:
        db.session.commit()
    except IntegrityError:
        # A student enrolled between the check and the delete; the foreign key caught it.
        db.session.rollback()
        raise _has_enrollments()


def _has_enrollments():
    return AppError(
        "COURSE_HAS_ENROLLMENTS",
        "This course has enrolled students and cannot be deleted.",
        409,
    )


def _owned_course(staff, course_id):
    """Return the course, or raise 404 if it does not exist and 403 if it is not yours."""
    course = db.session.get(Course, course_id)
    if course is None:
        raise AppError("NOT_FOUND", "Course not found.", 404)
    if course.staff_id != staff.id:
        raise AppError("FORBIDDEN", "You can only change your own courses.", 403)
    return course
