from collections.abc import Sequence
from functools import lru_cache

import bcrypt
from flask import current_app, has_app_context
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import AuditLog, User

DEFAULT_BCRYPT_ROUNDS = 12


def _bcrypt_rounds() -> int:
    """The configured work factor; the safe default outside a running app."""
    if has_app_context():
        return current_app.config.get("BCRYPT_ROUNDS", DEFAULT_BCRYPT_ROUNDS)
    return DEFAULT_BCRYPT_ROUNDS


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash of the password, as text."""
    salt = bcrypt.gensalt(rounds=_bcrypt_rounds())
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    # Used when the email is unknown, so a login takes the same time either way
    # and response timing does not reveal which emails have accounts.
    return hash_password("dummy-password-for-equal-timing")


def by_email_query(email: str) -> Select:
    """Find a user by email. Also used by the EXPLAIN report."""
    return db.select(User).filter_by(email=email.lower())


def login(email: str, password: str) -> User:
    """Return the user for correct credentials of an approved account.

    Wrong password and unknown email raise the same 401. The password is checked
    before the status, so a pending account is only revealed to its real owner.
    """
    user = db.session.execute(by_email_query(email)).scalar_one_or_none()
    stored_hash = user.password_hash if user is not None else _dummy_hash()
    password_ok = check_password(password, stored_hash)
    if user is None or not password_ok:
        raise AppError("UNAUTHORIZED", "Invalid email or password.", 401)
    if user.status != "approved":
        raise AppError("FORBIDDEN", "Your account is waiting for admin approval.", 403)
    return user


def register(name: str, email: str, password: str, role: str) -> User:
    """Create a pending student or staff account (US1)."""
    return _create_user(name, email, password, role=role, status="pending")


def create_admin(name: str, email: str, password: str) -> User:
    """Create an approved admin account (T1-1). Only reachable from the CLI."""
    return _create_user(name, email, password, role="admin", status="approved")


def list_pending() -> Sequence[User]:
    """All accounts waiting for approval, oldest first (US2)."""
    query = db.select(User).filter_by(status="pending").order_by(User.created_at, User.id)
    return db.session.execute(query).scalars().all()


def approve(user_id: int, actor: User) -> User:
    """Approve an account (US2) and record who did it (T4-4).

    The status change and the audit row are committed together: either both are
    saved or neither is. Approving an approved account changes nothing, so it
    writes no audit row.
    """
    user = db.session.get(User, user_id)
    if user is None:
        raise AppError("NOT_FOUND", "User not found.", 404)
    if user.status != "approved":
        user.status = "approved"
        db.session.add(_audit_entry(actor, "user.approve", "user", user.id))
        db.session.commit()
    return user


def _audit_entry(actor: User, action: str, target_type: str, target_id: int) -> AuditLog:
    return AuditLog(
        actor_id=actor.id, action=action, target_type=target_type, target_id=target_id
    )


def _create_user(name: str, email: str, password: str, role: str, status: str) -> User:
    """Save a new user. Raises AppError(EMAIL_TAKEN, 409) if the email is in use."""
    email = email.lower()
    taken = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if taken is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=status,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Two requests with the same email raced; the UNIQUE constraint caught it.
        db.session.rollback()
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)
    return user
