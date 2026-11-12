import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Course, Enrollment


@pytest.fixture()
def staff(make_user):
    """(staff_id, headers) for the course owner."""
    return make_user("staff")


@pytest.fixture()
def course_id(app, staff):
    staff_id, _ = staff
    with app.app_context():
        course = Course(title="Python Basics", description="", capacity=30, staff_id=staff_id)
        db.session.add(course)
        db.session.commit()
        return course.id


def enroll(client, headers, course_id):
    return client.post("/enrollments", json={"course_id": course_id}, headers=headers)


def enrollment_count(app, course_id, student_id=None):
    with app.app_context():
        query = db.select(db.func.count()).select_from(Enrollment).filter_by(course_id=course_id)
        if student_id is not None:
            query = query.filter_by(student_id=student_id)
        return db.session.execute(query).scalar_one()


def course_exists(app, course_id):
    with app.app_context():
        return db.session.get(Course, course_id) is not None


# ---------- enroll ----------

def test_us6_student_enrolls_and_gets_201(app, client, make_user, course_id):
    student_id, student = make_user("student")

    response = enroll(client, student, course_id)

    assert response.status_code == 201
    body = response.get_json()
    assert (body["student_id"], body["course_id"]) == (student_id, course_id)
    assert body["enrolled_at"]
    assert enrollment_count(app, course_id, student_id) == 1


def test_us6_enrolling_twice_returns_409_and_keeps_one_row(app, client, make_user, course_id):
    student_id, student = make_user("student")
    enroll(client, student, course_id)

    response = enroll(client, student, course_id)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "ALREADY_ENROLLED"
    assert enrollment_count(app, course_id, student_id) == 1


def test_us6_unknown_course_returns_404(client, make_user):
    _, student = make_user("student")

    response = enroll(client, student, 999999)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_us6_staff_and_admin_cannot_enroll(app, client, make_user, course_id, role):
    _, headers = make_user(role)

    response = enroll(client, headers, course_id)

    assert response.status_code == 403
    assert enrollment_count(app, course_id) == 0


@pytest.mark.parametrize(
    "body, field",
    [({}, "course_id"), ({"course_id": "1"}, "course_id"), ({"course_id": 0}, "course_id")],
)
def test_us6_invalid_body_returns_400(client, make_user, body, field):
    _, student = make_user("student")

    response = client.post("/enrollments", json=body, headers=student)

    assert response.status_code == 400
    assert field in response.get_json()["error"]["message"]


def test_us6_database_itself_rejects_a_duplicate_enrollment(app, make_user, course_id):
    student_id, _ = make_user("student")

    with app.app_context():
        db.session.add(Enrollment(student_id=student_id, course_id=course_id))
        db.session.commit()
        db.session.add(Enrollment(student_id=student_id, course_id=course_id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


# ---------- drop ----------

def test_us6_drop_returns_204_and_removes_the_row(app, client, make_user, course_id):
    student_id, student = make_user("student")
    enroll(client, student, course_id)

    response = client.delete(f"/enrollments/{course_id}", headers=student)

    assert response.status_code == 204
    assert enrollment_count(app, course_id, student_id) == 0


def test_us6_drop_when_not_enrolled_returns_404(client, make_user, course_id):
    _, student = make_user("student")

    response = client.delete(f"/enrollments/{course_id}", headers=student)

    assert response.status_code == 404


def test_us6_drop_for_unknown_course_returns_404(client, make_user):
    _, student = make_user("student")

    assert client.delete("/enrollments/999999", headers=student).status_code == 404


def test_us6_drop_only_removes_your_own_enrollment(app, client, make_user, course_id):
    a_id, student_a = make_user("student")
    b_id, student_b = make_user("student")
    enroll(client, student_a, course_id)
    enroll(client, student_b, course_id)

    client.delete(f"/enrollments/{course_id}", headers=student_a)

    assert enrollment_count(app, course_id, a_id) == 0
    assert enrollment_count(app, course_id, b_id) == 1


def test_us6_can_enroll_again_after_dropping(client, make_user, course_id):
    _, student = make_user("student")
    enroll(client, student, course_id)
    client.delete(f"/enrollments/{course_id}", headers=student)

    assert enroll(client, student, course_id).status_code == 201


def test_us6_staff_cannot_drop(client, staff, course_id):
    _, staff_headers = staff

    assert client.delete(f"/enrollments/{course_id}", headers=staff_headers).status_code == 403


@pytest.mark.parametrize("method, path", [("post", "/enrollments"), ("delete", "/enrollments/1")])
def test_us6_no_token_returns_401(client, method, path):
    response = getattr(client, method)(path, json={"course_id": 1})

    assert response.status_code == 401


# ---------- course delete rule ----------

def test_us6_deleting_a_course_with_students_returns_409(app, client, make_user, staff, course_id):
    _, owner = staff
    _, student = make_user("student")
    enroll(client, student, course_id)

    response = client.delete(f"/courses/{course_id}", headers=owner)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "COURSE_HAS_ENROLLMENTS"
    assert course_exists(app, course_id)


def test_us6_course_can_be_deleted_once_everyone_has_dropped(
    app, client, make_user, staff, course_id
):
    _, owner = staff
    _, student = make_user("student")
    enroll(client, student, course_id)
    client.delete(f"/enrollments/{course_id}", headers=student)

    response = client.delete(f"/courses/{course_id}", headers=owner)

    assert response.status_code == 204
    assert not course_exists(app, course_id)
