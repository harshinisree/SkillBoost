"""T4-5: the indexes from the design exist, and the key lookups use them.

A few hundred rows are inserted first, so MySQL's optimizer makes realistic
choices instead of scanning tiny tables.
"""
import pytest
from sqlalchemy import inspect, text

from app.extensions import db
from app.models import Course, Enrollment, User
from app.query_report import explain, key_queries
from app.services import course_service, enrollment_service, user_service


@pytest.fixture()
def realistic_data(app, client):
    """60 users, 30 courses, 300 enrollments; emptied afterwards by the client fixture."""
    with app.app_context():
        users = [
            User(name=f"User {n}", email=f"user{n}@example.com", password_hash="x", role="student", status="approved")
            for n in range(60)
        ]
        db.session.add_all(users)
        db.session.flush()
        courses = [
            Course(title=f"Course {n}", description="", capacity=100, staff_id=users[0].id) for n in range(30)
        ]
        db.session.add_all(courses)
        db.session.flush()
        db.session.add_all(
            Enrollment(student_id=users[s].id, course_id=courses[c].id)
            for s in range(1, 31)
            for c in range(10)
        )
        db.session.commit()
        for table in ("users", "courses", "enrollments"):
            db.session.execute(text(f"ANALYZE TABLE {table}"))
        ids = {"student": users[5].id, "course": courses[3].id}
    return ids


def plan(app, statement, table):
    with app.app_context():
        [row] = [r for r in explain(statement) if r["table"] == table]
        return row


def test_t4_5_design_indexes_exist(app):
    with app.app_context():
        inspector = inspect(db.engine)
        indexed = {
            table: {tuple(i["column_names"]) for i in inspector.get_indexes(table)}
            | {tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)}
            for table in ("users", "courses", "enrollments", "audit_log")
        }
    assert ("email",) in indexed["users"]
    assert ("staff_id",) in indexed["courses"]
    assert ("course_id",) in indexed["enrollments"]
    assert ("student_id", "course_id") in indexed["enrollments"]
    assert ("target_type", "target_id") in indexed["audit_log"]


def test_t4_5_login_lookup_uses_the_email_index(app, realistic_data):
    row = plan(app, user_service.by_email_query("user7@example.com"), "users")

    assert row["key"] == "email"
    assert int(row["rows"]) == 1  # some MySQL versions report this as text


def test_t4_5_duplicate_check_uses_the_unique_index(app, realistic_data):
    statement = enrollment_service.enrollment_query(realistic_data["student"], realistic_data["course"])

    assert plan(app, statement, "enrollments")["key"] == "uq_enrollments_student_course"


def test_t4_5_seat_count_uses_the_course_index(app, realistic_data):
    statement = enrollment_service.seat_count_query(realistic_data["course"])

    assert plan(app, statement, "enrollments")["key"] == "ix_enrollments_course_id"


def test_t4_5_my_enrollments_uses_indexes_on_both_tables(app, realistic_data):
    statement = enrollment_service.my_enrollments_query(realistic_data["student"])

    assert plan(app, statement, "enrollments")["key"] == "uq_enrollments_student_course"
    assert plan(app, statement, "courses")["key"] == "PRIMARY"


def test_t4_5_report_covers_every_key_query(app, runner, realistic_data):
    result = runner.invoke(args=["explain-queries"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        names = [name for name, _ in key_queries()]
    for name in names:
        assert name in result.output
    assert result.output.startswith("| Query | Table |")


def test_t4_5_shared_course_list_query_still_serves_the_api(app, client, make_user, realistic_data):
    _, headers = make_user("student")

    body = client.get("/courses", query_string={"q": "course 1", "sort": "title"}, headers=headers).get_json()

    assert body["total"] == 11  # Course 1, Course 10 .. Course 19
    assert [c["title"] for c in body["items"]][:2] == ["Course 1", "Course 10"]
    with app.app_context():
        assert len(db.session.execute(course_service.list_query(q="course 1")).scalars().all()) == 11
