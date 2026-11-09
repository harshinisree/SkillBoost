from app import create_app
from app.errors import AppError


def test_app_error_returns_standard_json():
    # Unit test: no real database is used (in-memory SQLite is never queried).
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})

    @app.get("/boom")
    def boom():
        raise AppError("COURSE_FULL", "This course has no seats left.", 409)

    response = app.test_client().get("/boom")

    assert response.status_code == 409
    assert response.get_json() == {
        "error": {"code": "COURSE_FULL", "message": "This course has no seats left."}
    }
