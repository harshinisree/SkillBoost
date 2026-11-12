"""End-to-end: register, approve, log in, create a course, enroll, list, drop."""
from app.services import user_service

PASSWORD = "StrongPass1"


def login(client, email):
    token = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": "Bearer " + token.get_json()["access_token"]}


def register(client, name, email, role):
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": PASSWORD, "role": role},
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def test_us7_full_student_journey(app, client):
    with app.app_context():
        user_service.create_admin("Admin User", "admin@example.com", PASSWORD)
    admin = login(client, "admin@example.com")

    # 1. A teacher and a student register; the admin approves both.
    staff_id = register(client, "Meena Iyer", "meena@example.com", "staff")
    student_id = register(client, "Ravi Kumar", "ravi@example.com", "student")
    for user_id in (staff_id, student_id):
        assert client.post(f"/admin/approve/{user_id}", headers=admin).status_code == 200

    # 2. Both log in; the teacher creates a course.
    staff = login(client, "meena@example.com")
    student = login(client, "ravi@example.com")
    course = client.post(
        "/courses",
        json={"title": "Python Basics", "description": "Start here.", "capacity": 30},
        headers=staff,
    ).get_json()

    # 3. The student finds the course, enrolls, and sees it in their list.
    found = client.get("/courses", query_string={"q": "python"}, headers=student).get_json()
    assert [c["id"] for c in found["items"]] == [course["id"]]
    assert client.post("/enrollments", json={"course_id": course["id"]}, headers=student).status_code == 201
    mine = client.get("/enrollments/me", headers=student).get_json()["items"]
    assert [(i["course_id"], i["title"]) for i in mine] == [(course["id"], "Python Basics")]

    # 4. The student drops it, and the list is empty again.
    assert client.delete(f"/enrollments/{course['id']}", headers=student).status_code == 204
    assert client.get("/enrollments/me", headers=student).get_json()["items"] == []
