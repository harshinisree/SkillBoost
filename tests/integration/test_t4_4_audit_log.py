"""T4-4: every approval leaves an audit row, written in the same transaction."""
import pytest

from app.extensions import db
from app.models import AuditLog, User
from app.services import user_service


@pytest.fixture()
def admin(make_user):
    return make_user("admin")  # (admin_id, headers)


@pytest.fixture()
def pending_id(app):
    with app.app_context():
        user = user_service.register("Asha Rao", "asha@example.com", "StrongPass1", "student")
        return user.id


def audit_rows(app):
    with app.app_context():
        return [row.to_dict() for row in db.session.execute(db.select(AuditLog)).scalars()]


def status_of(app, user_id):
    with app.app_context():
        return db.session.get(User, user_id).status


def approve(client, headers, user_id):
    return client.post(f"/admin/approve/{user_id}", headers=headers)


def test_t4_4_approval_writes_one_audit_row(app, client, admin, pending_id):
    admin_id, headers = admin

    assert approve(client, headers, pending_id).status_code == 200

    [row] = audit_rows(app)
    assert row["actor_id"] == admin_id
    assert row["action"] == "user.approve"
    assert (row["target_type"], row["target_id"]) == ("user", pending_id)
    assert row["created_at"]


def test_t4_4_approving_twice_writes_no_second_row(app, client, admin, pending_id):
    _, headers = admin
    approve(client, headers, pending_id)

    approve(client, headers, pending_id)

    assert len(audit_rows(app)) == 1


def test_t4_4_unknown_user_writes_no_row(app, client, admin):
    _, headers = admin

    assert approve(client, headers, 999999).status_code == 404
    assert audit_rows(app) == []


def test_t4_4_forbidden_attempt_writes_no_row(app, client, make_user, pending_id):
    _, staff = make_user("staff")

    assert approve(client, staff, pending_id).status_code == 403
    assert audit_rows(app) == []
    assert status_of(app, pending_id) == "pending"


def test_t4_4_if_the_audit_row_fails_the_approval_is_undone(
    app, client, admin, pending_id, monkeypatch
):
    """Same transaction: a broken audit row (no actor) must roll back the approval too."""
    from app.models import AuditLog as RealAuditLog

    def broken_entry(actor, action, target_type, target_id):
        return RealAuditLog(actor_id=None, action=action, target_type=target_type, target_id=target_id)

    monkeypatch.setattr(user_service, "_audit_entry", broken_entry)
    _, headers = admin

    response = approve(client, headers, pending_id)

    assert response.status_code == 500
    assert status_of(app, pending_id) == "pending"
    assert audit_rows(app) == []
