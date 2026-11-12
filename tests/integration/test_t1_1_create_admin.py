import bcrypt

from app.extensions import db
from app.models import User

ANSWERS = "Admin User\nadmin@example.com\nStrongPass1\nStrongPass1\n"


def users_with_email(app, email):
    with app.app_context():
        rows = db.session.execute(db.select(User).filter_by(email=email)).scalars().all()
        return [{"role": u.role, "status": u.status, "hash": u.password_hash} for u in rows]


def test_t1_1_create_admin_prompts_for_name_email_and_password(runner):
    result = runner.invoke(args=["create-admin"], input=ANSWERS)

    assert result.exit_code == 0, result.output
    assert "Name:" in result.output
    assert "Email:" in result.output
    assert "Password:" in result.output
    assert "Admin admin@example.com created." in result.output


def test_t1_1_create_admin_never_shows_the_password(runner):
    result = runner.invoke(args=["create-admin"], input=ANSWERS)

    assert result.exit_code == 0, result.output
    assert "StrongPass1" not in result.output


def test_t1_1_new_user_is_an_approved_admin(runner, app):
    runner.invoke(args=["create-admin"], input=ANSWERS)

    [row] = users_with_email(app, "admin@example.com")
    assert row["role"] == "admin"
    assert row["status"] == "approved"
    assert bcrypt.checkpw(b"StrongPass1", row["hash"].encode("utf-8"))


def test_t1_1_existing_email_fails_clearly_and_creates_nothing(runner, app, client):
    client.post(
        "/auth/register",
        json={
            "name": "Asha Rao",
            "email": "admin@example.com",
            "password": "StrongPass1",
            "role": "student",
        },
    )

    result = runner.invoke(args=["create-admin"], input=ANSWERS)

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert "Nothing was created" in result.output
    rows = users_with_email(app, "admin@example.com")
    assert len(rows) == 1
    assert rows[0]["role"] == "student"


def test_t1_1_invalid_email_fails_and_creates_nothing(runner, app):
    result = runner.invoke(
        args=["create-admin"], input="Admin User\nnot-an-email\nStrongPass1\nStrongPass1\n"
    )

    assert result.exit_code != 0
    assert "email" in result.output
    assert users_with_email(app, "not-an-email") == []


def test_t1_1_short_password_fails_and_creates_nothing(runner, app):
    result = runner.invoke(
        args=["create-admin"], input="Admin User\nadmin@example.com\nshort\nshort\n"
    )

    assert result.exit_code != 0
    assert "password" in result.output
    assert users_with_email(app, "admin@example.com") == []
