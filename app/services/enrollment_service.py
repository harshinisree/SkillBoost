from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import Course, Enrollment


def enroll(student, course_id):
    """Enroll a student, never past the course's capacity (US6, US6b).

    The course row is locked (SELECT ... FOR UPDATE) before anything is checked,
    so concurrent requests for the same course run one at a time and two
    students can never both take the last seat. The lock is released by the
    commit or rollback that ends the transaction.

    The duplicate check and the seat count are locking reads too. Under MySQL's
    default REPEATABLE READ, a plain SELECT reads from a snapshot taken at the
    transaction's first read (loading the logged-in user, before this request
    waited for the lock), so it would miss seats taken while it waited.
    Locking reads always see the latest committed rows.
    """
    course = db.session.execute(
        db.select(Course).filter_by(id=course_id).with_for_update()
    ).scalar_one_or_none()
    if course is None:
        _fail(AppError("NOT_FOUND", "Course not found.", 404))
    if _find(student, course_id, lock=True) is not None:
        _fail(_already_enrolled())

    seats_taken = db.session.execute(seat_count_query(course_id).with_for_update()).scalar_one()
    if seats_taken >= course.capacity:
        _fail(AppError("COURSE_FULL", "This course has no seats left.", 409))

    enrollment = Enrollment(student_id=student.id, course_id=course_id)
    db.session.add(enrollment)
    try:
        db.session.commit()
    except IntegrityError:
        # Same student, two identical requests: the UNIQUE constraint caught it.
        db.session.rollback()
        raise _already_enrolled()
    return enrollment


def _fail(error):
    """End the transaction (releasing the lock) and raise the error."""
    db.session.rollback()
    raise error


def list_for_student(student):
    """The student's own enrollments with course titles, newest first (US7).

    One joined query, however many enrollments there are.
    """
    query = my_enrollments_query(student.id)
    return [
        {
            "course_id": row.course_id,
            "title": row.title,
            "enrolled_at": row.enrolled_at.isoformat() if row.enrolled_at else None,
        }
        for row in db.session.execute(query)
    ]


def drop(student, course_id):
    """Remove the student's own enrollment. 404 if they are not enrolled."""
    enrollment = _find(student, course_id)
    if enrollment is None:
        raise AppError("NOT_FOUND", "You are not enrolled in this course.", 404)
    db.session.delete(enrollment)
    db.session.commit()


def seat_count_query(course_id):
    """How many seats a course has taken. Also used by the EXPLAIN report."""
    return db.select(func.count()).select_from(Enrollment).filter_by(course_id=course_id)


def enrollment_query(student_id, course_id):
    """One student's enrollment in one course. Also used by the EXPLAIN report."""
    return db.select(Enrollment).filter_by(student_id=student_id, course_id=course_id)


def my_enrollments_query(student_id):
    """A student's enrollments with course titles. Also used by the EXPLAIN report."""
    return (
        db.select(Enrollment.course_id, Course.title, Enrollment.enrolled_at)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.student_id == student_id)
        .order_by(Enrollment.enrolled_at.desc(), Enrollment.id.desc())
    )


def _find(student, course_id, lock=False):
    query = enrollment_query(student.id, course_id)
    if lock:
        query = query.with_for_update()
    return db.session.execute(query).scalar_one_or_none()


def _already_enrolled():
    return AppError("ALREADY_ENROLLED", "You are already enrolled in this course.", 409)
