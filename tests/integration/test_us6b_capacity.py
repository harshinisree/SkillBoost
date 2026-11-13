"""US6b: a course can never be oversold, even under concurrent requests."""
import threading
from collections import Counter

import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Course, Enrollment


@pytest.fixture()
def make_course(app, make_user):
    staff_id, _ = make_user("staff")

    def _make(capacity):
        with app.app_context():
            course = Course(title="Python Basics", description="", capacity=capacity, staff_id=staff_id)
            db.session.add(course)
            db.session.commit()
            return course.id

    return _make


def enroll(client, headers, course_id):
    return client.post("/enrollments", json={"course_id": course_id}, headers=headers)


def rows_for(app, course_id):
    with app.app_context():
        query = db.select(db.func.count()).select_from(Enrollment).filter_by(course_id=course_id)
        return db.session.execute(query).scalar_one()


def enroll_all_at_once(app, headers_list, course_id):
    """Send one enroll request per headers entry, all released at the same moment.

    Each thread has its own test client, so each request gets its own app
    context, its own database session, and its own MySQL connection.
    """
    start = threading.Barrier(len(headers_list))
    statuses = [None] * len(headers_list)

    def worker(index, headers):
        client = app.test_client()
        start.wait()
        try:
            statuses[index] = enroll(client, headers, course_id).status_code
        except SQLAlchemyError as err:  # e.g. a deadlock, if the locking were wrong
            statuses[index] = type(err).__name__

    threads = [threading.Thread(target=worker, args=(i, h)) for i, h in enumerate(headers_list)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return statuses


# ---------- the seat limit, one request at a time ----------

def test_us6b_full_course_returns_409_course_full(app, client, make_user, make_course):
    course_id = make_course(capacity=2)
    students = [make_user("student")[1] for _ in range(3)]

    first, second, third = (enroll(client, s, course_id) for s in students)

    assert (first.status_code, second.status_code) == (201, 201)
    assert third.status_code == 409
    assert third.get_json()["error"]["code"] == "COURSE_FULL"
    assert rows_for(app, course_id) == 2


def test_us6b_dropping_frees_a_seat(app, client, make_user, make_course):
    course_id = make_course(capacity=1)
    _, student_a = make_user("student")
    _, student_b = make_user("student")
    enroll(client, student_a, course_id)
    assert enroll(client, student_b, course_id).status_code == 409

    client.delete(f"/enrollments/{course_id}", headers=student_a)

    assert enroll(client, student_b, course_id).status_code == 201


def test_us6b_duplicate_is_reported_before_full(client, make_user, make_course):
    course_id = make_course(capacity=1)
    _, student = make_user("student")
    enroll(client, student, course_id)

    response = enroll(client, student, course_id)

    assert response.get_json()["error"]["code"] == "ALREADY_ENROLLED"


def test_us6b_enroll_locks_the_course_row_first(app, client, make_user, make_course):
    course_id = make_course(capacity=5)
    _, student = make_user("student")
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(" ".join(statement.split()).upper())

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        assert enroll(client, student, course_id).status_code == 201
    finally:
        event.remove(engine, "before_cursor_execute", record)

    locking = [i for i, s in enumerate(statements) if "FROM COURSES" in s and "FOR UPDATE" in s]
    counting = [i for i, s in enumerate(statements) if "COUNT(" in s and "ENROLLMENTS" in s]
    assert locking, "the course row must be read with SELECT ... FOR UPDATE"
    assert locking[0] < counting[0], "the lock must come before the seat count"
    assert "FOR UPDATE" in statements[counting[0]], (
        "the seat count must be a locking read, or REPEATABLE READ serves a stale snapshot"
    )


# ---------- the race ----------

def test_us6b_ten_students_racing_for_three_seats(app, make_user, make_course):
    course_id = make_course(capacity=3)
    students = [make_user("student")[1] for _ in range(10)]

    statuses = enroll_all_at_once(app, students, course_id)

    assert Counter(statuses) == Counter({201: 3, 409: 7}), dict(Counter(statuses))
    assert rows_for(app, course_id) == 3


def test_us6b_same_student_double_click(app, make_user, make_course):
    course_id = make_course(capacity=5)
    _, student = make_user("student")

    statuses = enroll_all_at_once(app, [student, student], course_id)

    assert Counter(statuses) == Counter({201: 1, 409: 1}), dict(Counter(statuses))
    assert rows_for(app, course_id) == 1
