"""T4-6: flask seed loads usable demo data and can be run twice safely."""
import pytest

from app.extensions import db
from app.models import AuditLog, Course, Enrollment, User
from app.seed import DEMO_PASSWORD, demo_logins


def counts(app):
    with app.app_context():
        def count(model, **filters):
            query = db.select(db.func.count()).select_from(model).filter_by(**filters)
            return db.session.execute(query).scalar_one()

        return {
            "admin": count(User, role="admin"),
            "staff": count(User, role="staff", status="approved"),
            "students": count(User, role="student", status="approved"),
            "pending": count(User, status="pending"),
            "courses": count(Course),
            "enrollments": count(Enrollment),
            "audit": count(AuditLog),
        }


@pytest.fixture()
def seeded(app, runner):
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    return result.output


def test_t4_6_seed_creates_the_demo_data(app, seeded):
    assert counts(app) == {
        "admin": 1,
        "staff": 2,
        "students": 5,
        "pending": 1,
        "courses": 10,
        "enrollments": 12,
        "audit": 7,  # one per approval: 2 staff and 5 students
    }
    assert "Added 9 users, 10 courses, 12 enrollments." in seeded


def test_t4_6_seed_includes_one_full_course(app, seeded):
    with app.app_context():
        course = db.session.execute(db.select(Course).filter_by(title="System Design Basics")).scalar_one()
        taken = db.session.execute(
            db.select(db.func.count()).select_from(Enrollment).filter_by(course_id=course.id)
        ).scalar_one()
    assert taken == course.capacity == 2


def test_t4_6_seed_twice_adds_nothing(app, runner, seeded):
    before = counts(app)

    second = runner.invoke(args=["seed"])

    assert "Added 0 users, 0 courses, 0 enrollments." in second.output
    assert counts(app) == before


@pytest.mark.parametrize("role, expected_status", [("admin", 200), ("staff", 200), ("student", 200)])
def test_t4_6_demo_accounts_can_log_in(client, seeded, role, expected_status):
    email = next(e for r, e in demo_logins() if r == role)

    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})

    assert response.status_code == expected_status


def test_t4_6_pending_demo_student_must_wait_for_approval(client, seeded):
    email = next(e for r, e in demo_logins() if "pending" in r)

    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})

    assert response.status_code == 403
