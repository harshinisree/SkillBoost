import pytest

from app.extensions import db
from app.models import Course

COURSE = {"title": "Python Basics", "description": "Start here.", "capacity": 30}


def create(client, headers, **overrides):
    return client.post("/courses", json={**COURSE, **overrides}, headers=headers)


def stored_course(app, course_id):
    with app.app_context():
        course = db.session.get(Course, course_id)
        return None if course is None else course.to_dict()


# ---------- create ----------

def test_us4_staff_creates_course_and_owns_it(app, client, make_user):
    staff_id, staff = make_user("staff")

    response = create(client, staff)

    assert response.status_code == 201
    body = response.get_json()
    assert body["title"] == "Python Basics"
    assert body["description"] == "Start here."
    assert body["capacity"] == 30
    assert body["staff_id"] == staff_id
    assert stored_course(app, body["id"])["staff_id"] == staff_id


@pytest.mark.parametrize("role", ["student", "admin"])
def test_us4_non_staff_cannot_create_a_course(client, make_user, role):
    _, headers = make_user(role)

    response = create(client, headers)

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_us4_create_without_token_returns_401(client):
    assert client.post("/courses", json=COURSE).status_code == 401


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"capacity": 0}, "capacity"),
        ({"capacity": -5}, "capacity"),
        ({"capacity": "30"}, "capacity"),
        ({"capacity": None}, "capacity"),
    ],
)
def test_us4_invalid_course_returns_400_naming_the_field(client, make_user, overrides, field):
    _, staff = make_user("staff")

    response = create(client, staff, **overrides)

    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["message"]


@pytest.mark.parametrize("missing", ["title", "capacity"])
def test_us4_missing_required_field_returns_400(client, make_user, missing):
    _, staff = make_user("staff")
    payload = {k: v for k, v in COURSE.items() if k != missing}

    response = client.post("/courses", json=payload, headers=staff)

    assert response.status_code == 400
    assert missing in response.get_json()["error"]["message"]


# ---------- update ----------

def test_us4_owner_updates_course_and_gets_200(app, client, make_user):
    _, staff = make_user("staff")
    course_id = create(client, staff).get_json()["id"]
    changes = {"title": "Python Advanced", "description": "Next step.", "capacity": 12}

    response = client.put(f"/courses/{course_id}", json=changes, headers=staff)

    assert response.status_code == 200
    assert response.get_json()["title"] == "Python Advanced"
    stored = stored_course(app, course_id)
    assert (stored["title"], stored["description"], stored["capacity"]) == (
        "Python Advanced",
        "Next step.",
        12,
    )


def test_us4_other_staff_cannot_update_and_nothing_changes(app, client, make_user):
    _, owner = make_user("staff")
    _, other = make_user("staff")
    course_id = create(client, owner).get_json()["id"]

    response = client.put(
        f"/courses/{course_id}", json={**COURSE, "title": "Hijacked"}, headers=other
    )

    assert response.status_code == 403
    assert stored_course(app, course_id)["title"] == "Python Basics"


def test_us4_update_unknown_course_returns_404(client, make_user):
    _, staff = make_user("staff")

    response = client.put("/courses/999999", json=COURSE, headers=staff)

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_us4_update_with_invalid_body_returns_400(client, make_user):
    _, staff = make_user("staff")
    course_id = create(client, staff).get_json()["id"]

    response = client.put(f"/courses/{course_id}", json={**COURSE, "capacity": 0}, headers=staff)

    assert response.status_code == 400


# ---------- delete ----------

def test_us4_owner_deletes_course_and_gets_204(app, client, make_user):
    _, staff = make_user("staff")
    course_id = create(client, staff).get_json()["id"]

    response = client.delete(f"/courses/{course_id}", headers=staff)

    assert response.status_code == 204
    assert stored_course(app, course_id) is None


def test_us4_other_staff_cannot_delete_and_course_stays(app, client, make_user):
    _, owner = make_user("staff")
    _, other = make_user("staff")
    course_id = create(client, owner).get_json()["id"]

    response = client.delete(f"/courses/{course_id}", headers=other)

    assert response.status_code == 403
    assert stored_course(app, course_id) is not None


def test_us4_delete_unknown_course_returns_404(client, make_user):
    _, staff = make_user("staff")

    assert client.delete("/courses/999999", headers=staff).status_code == 404


# ---------- access on update and delete ----------

@pytest.mark.parametrize("method", ["put", "delete"])
def test_us4_student_cannot_update_or_delete(client, make_user, method):
    _, staff = make_user("staff")
    _, student = make_user("student")
    course_id = create(client, staff).get_json()["id"]

    response = getattr(client, method)(f"/courses/{course_id}", json=COURSE, headers=student)

    assert response.status_code == 403


@pytest.mark.parametrize("method", ["put", "delete"])
def test_us4_update_or_delete_without_token_returns_401(client, method):
    response = getattr(client, method)("/courses/1", json=COURSE)

    assert response.status_code == 401
