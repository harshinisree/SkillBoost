import pytest

from app.extensions import db
from app.models import Course


def add_courses(app, staff_id, titles):
    """Insert courses directly; returns their ids in creation order."""
    with app.app_context():
        courses = [Course(title=t, description="", capacity=10, staff_id=staff_id) for t in titles]
        db.session.add_all(courses)
        db.session.commit()
        return [c.id for c in courses]


@pytest.fixture()
def viewer(make_user):
    _, headers = make_user("student")
    return headers


@pytest.fixture()
def staff_id(make_user):
    user_id, _ = make_user("staff")
    return user_id


def browse(client, headers, **params):
    return client.get("/courses", query_string=params, headers=headers)


def titles(response):
    return [item["title"] for item in response.get_json()["items"]]


def test_us5_list_returns_items_and_paging_fields(app, client, viewer, staff_id):
    add_courses(app, staff_id, ["A", "B", "C"])

    response = browse(client, viewer)

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["items"]) == 3
    assert (body["page"], body["per_page"], body["total"]) == (1, 20, 3)


def test_us5_defaults_split_25_courses_into_pages_of_20_and_5(app, client, viewer, staff_id):
    ids = add_courses(app, staff_id, [f"Course {n:02d}" for n in range(25)])

    first = browse(client, viewer).get_json()
    second = browse(client, viewer, page=2).get_json()

    assert len(first["items"]) == 20
    assert len(second["items"]) == 5
    assert first["total"] == second["total"] == 25
    seen = [c["id"] for c in first["items"] + second["items"]]
    assert sorted(seen) == sorted(ids)  # every course exactly once, no overlap


def test_us5_page_past_the_end_is_empty(app, client, viewer, staff_id):
    add_courses(app, staff_id, ["A", "B"])

    body = browse(client, viewer, page=5).get_json()

    assert body["items"] == []
    assert body["total"] == 2


def test_us5_per_page_above_100_is_capped_at_100(app, client, viewer, staff_id):
    add_courses(app, staff_id, [f"Course {n:03d}" for n in range(105)])

    body = browse(client, viewer, per_page=500).get_json()

    assert body["per_page"] == 100
    assert len(body["items"]) == 100
    assert body["total"] == 105


def test_us5_q_filters_by_title_ignoring_case(app, client, viewer, staff_id):
    add_courses(app, staff_id, ["Python Basics", "Advanced PYTHON", "SQL Fundamentals"])

    response = browse(client, viewer, q="python", sort="title")

    assert titles(response) == ["Advanced PYTHON", "Python Basics"]
    assert response.get_json()["total"] == 2


def test_us5_q_treats_percent_and_underscore_as_plain_text(app, client, viewer, staff_id):
    add_courses(app, staff_id, ["100% Python", "Python", "snake_case style"])

    assert titles(browse(client, viewer, q="%")) == ["100% Python"]
    assert titles(browse(client, viewer, q="_")) == ["snake_case style"]


def test_us5_sort_by_title_both_directions(app, client, viewer, staff_id):
    add_courses(app, staff_id, ["Cherry", "Apple", "Banana"])

    assert titles(browse(client, viewer, sort="title")) == ["Apple", "Banana", "Cherry"]
    assert titles(browse(client, viewer, sort="-title")) == ["Cherry", "Banana", "Apple"]


def test_us5_sort_by_created_at_both_directions(app, client, viewer, staff_id):
    ids = add_courses(app, staff_id, ["First", "Second", "Third"])

    oldest_first = [c["id"] for c in browse(client, viewer, sort="created_at").get_json()["items"]]
    newest_first = [c["id"] for c in browse(client, viewer, sort="-created_at").get_json()["items"]]

    assert oldest_first == ids
    assert newest_first == list(reversed(ids))


def test_us5_default_sort_is_newest_first(app, client, viewer, staff_id):
    ids = add_courses(app, staff_id, ["First", "Second", "Third"])

    default = [c["id"] for c in browse(client, viewer).get_json()["items"]]

    assert default == list(reversed(ids))


@pytest.mark.parametrize("bad_sort", ["price", "TITLE", "title;DROP TABLE courses", ""])
def test_us5_unknown_sort_returns_400(client, viewer, bad_sort):
    response = browse(client, viewer, sort=bad_sort)

    assert response.status_code == 400
    assert "sort" in response.get_json()["error"]["message"]


@pytest.mark.parametrize(
    "params, field",
    [({"page": 0}, "page"), ({"page": "abc"}, "page"), ({"per_page": 0}, "per_page")],
)
def test_us5_invalid_paging_returns_400(client, viewer, params, field):
    response = browse(client, viewer, **params)

    assert response.status_code == 400
    assert field in response.get_json()["error"]["message"]


def test_us5_no_token_returns_401(client):
    assert client.get("/courses").status_code == 401


@pytest.mark.parametrize("role", ["student", "staff", "admin"])
def test_us5_every_approved_role_can_browse(client, make_user, role):
    _, headers = make_user(role)

    assert browse(client, headers).status_code == 200
