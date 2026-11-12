import pytest
from sqlalchemy import event

from app.extensions import db
from app.models import Course


def add_courses(app, staff_id, titles):
    with app.app_context():
        courses = [Course(title=t, description="", capacity=10, staff_id=staff_id) for t in titles]
        db.session.add_all(courses)
        db.session.commit()
        return [c.id for c in courses]


def enroll(client, headers, course_id):
    assert client.post("/enrollments", json={"course_id": course_id}, headers=headers).status_code == 201


def my_items(client, headers):
    response = client.get("/enrollments/me", headers=headers)
    assert response.status_code == 200
    return response.get_json()["items"]


@pytest.fixture()
def staff_id(make_user):
    user_id, _ = make_user("staff")
    return user_id


def test_us7_lists_course_id_title_and_enrolled_date(app, client, make_user, staff_id):
    python_id, sql_id = add_courses(app, staff_id, ["Python Basics", "SQL Fundamentals"])
    _, student = make_user("student")
    enroll(client, student, python_id)
    enroll(client, student, sql_id)

    items = my_items(client, student)

    assert {(i["course_id"], i["title"]) for i in items} == {
        (python_id, "Python Basics"),
        (sql_id, "SQL Fundamentals"),
    }
    assert all(i["enrolled_at"] for i in items)


def test_us7_student_a_never_sees_student_b(app, client, make_user, staff_id):
    a_course, b_course = add_courses(app, staff_id, ["A's course", "B's course"])
    _, student_a = make_user("student")
    _, student_b = make_user("student")
    enroll(client, student_a, a_course)
    enroll(client, student_b, b_course)

    assert [i["course_id"] for i in my_items(client, student_a)] == [a_course]
    assert [i["course_id"] for i in my_items(client, student_b)] == [b_course]


def test_us7_student_with_no_enrollments_gets_empty_list(client, make_user):
    _, student = make_user("student")

    assert my_items(client, student) == []


def test_us7_dropped_course_disappears_from_the_list(app, client, make_user, staff_id):
    [course_id] = add_courses(app, staff_id, ["Python Basics"])
    _, student = make_user("student")
    enroll(client, student, course_id)

    client.delete(f"/enrollments/{course_id}", headers=student)

    assert my_items(client, student) == []


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_us7_staff_and_admin_get_403(client, make_user, role):
    _, headers = make_user(role)

    response = client.get("/enrollments/me", headers=headers)

    assert response.status_code == 403


def test_us7_no_token_returns_401(client):
    assert client.get("/enrollments/me").status_code == 401


def count_queries_during(app, action):
    """Run action() and return how many SELECT statements hit the database."""
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        action()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return len(statements)


def test_us7_list_uses_one_joined_query_however_many_rows(app, client, make_user, staff_id):
    course_ids = add_courses(app, staff_id, [f"Course {n}" for n in range(6)])
    _, one = make_user("student")
    _, six = make_user("student")
    enroll(client, one, course_ids[0])
    for course_id in course_ids:
        enroll(client, six, course_id)

    queries_for_one = count_queries_during(app, lambda: my_items(client, one))
    queries_for_six = count_queries_during(app, lambda: my_items(client, six))

    # One query loads the logged-in user, one joined query loads the list.
    assert queries_for_one == queries_for_six == 2
