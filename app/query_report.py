"""EXPLAIN the app's most important queries (T4-5).

Each entry uses the same query function as the real code, so the report always
describes exactly what the app sends to MySQL.
"""
from sqlalchemy import text

from .extensions import db
from .models import Enrollment, User
from .services import course_service, enrollment_service, user_service


def _sample_values():
    """A real email and a real enrollment from the database, so every plan is realistic.

    With values that match nothing, MySQL reports "Impossible WHERE" and shows no plan.
    """
    email = db.session.execute(db.select(User.email).limit(1)).scalar() or "someone@example.com"
    pair = db.session.execute(db.select(Enrollment.student_id, Enrollment.course_id).limit(1)).first()
    student_id, course_id = pair if pair else (1, 1)
    return email, student_id, course_id


def key_queries():
    """(name, statement) pairs, filled with values taken from the database."""
    email, student_id, course_id = _sample_values()
    return [
        ("Login: find user by email", user_service.by_email_query(email)),
        ("Enroll: duplicate check", enrollment_service.enrollment_query(student_id, course_id)),
        ("Enroll: seat count", enrollment_service.seat_count_query(course_id)),
        ("My enrollments (with course titles)", enrollment_service.my_enrollments_query(student_id)),
        ("Course list, newest first", course_service.list_query().limit(20)),
        ("Course list, title search", course_service.list_query(q="python").limit(20)),
    ]


def explain(statement):
    """Run EXPLAIN on a statement and return MySQL's plan, one dict per table."""
    sql = str(statement.compile(dialect=db.engine.dialect, compile_kwargs={"literal_binds": True}))
    return [dict(row) for row in db.session.execute(text("EXPLAIN " + sql)).mappings()]


def markdown_report():
    """The plans as a Markdown table, ready to paste into the README."""
    lines = [
        "| Query | Table | Access type | Index used | Rows examined | Extra |",
        "|---|---|---|---|---|---|",
    ]
    for name, statement in key_queries():
        for row in explain(statement):
            lines.append(
                f"| {name} | {row.get('table')} | {row.get('type')} | {row.get('key') or 'none'} "
                f"| {row.get('rows')} | {row.get('Extra') or ''} |"
            )
    return "\n".join(lines)
