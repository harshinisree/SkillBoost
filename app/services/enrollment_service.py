from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import Course, Enrollment


def enroll(student, course_id):
    """Enroll a student in a course (US6). The seat limit comes in US6b."""
    if db.session.get(Course, course_id) is None:
        raise AppError("NOT_FOUND", "Course not found.", 404)
    if _find(student, course_id) is not None:
        raise _already_enrolled()

    enrollment = Enrollment(student_id=student.id, course_id=course_id)
    db.session.add(enrollment)
    try:
        db.session.commit()
    except IntegrityError:
        # Two identical requests raced; the UNIQUE (student_id, course_id) caught it.
        db.session.rollback()
        raise _already_enrolled()
    return enrollment


def drop(student, course_id):
    """Remove the student's own enrollment. 404 if they are not enrolled."""
    enrollment = _find(student, course_id)
    if enrollment is None:
        raise AppError("NOT_FOUND", "You are not enrolled in this course.", 404)
    db.session.delete(enrollment)
    db.session.commit()


def _find(student, course_id):
    query = db.select(Enrollment).filter_by(student_id=student.id, course_id=course_id)
    return db.session.execute(query).scalar_one_or_none()


def _already_enrolled():
    return AppError("ALREADY_ENROLLED", "You are already enrolled in this course.", 409)
