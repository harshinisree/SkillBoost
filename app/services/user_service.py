from functools import lru_cache

import bcrypt
from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import User


def hash_password(password):
    """Return a salted bcrypt hash of the password, as text."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


@lru_cache(maxsize=1)
def _dummy_hash():
    # Used when the email is unknown, so a login takes the same time either way
    # and response timing does not reveal which emails have accounts.
    return hash_password("dummy-password-for-equal-timing")


def login(email, password):
    """Return the user for correct credentials of an approved account.

    Wrong password and unknown email raise the same 401. The password is checked
    before the status, so a pending account is only revealed to its real owner.
    """
    user = db.session.execute(
        db.select(User).filter_by(email=email.lower())
    ).scalar_one_or_none()
    stored_hash = user.password_hash if user is not None else _dummy_hash()
    password_ok = check_password(password, stored_hash)
    if user is None or not password_ok:
        raise AppError("UNAUTHORIZED", "Invalid email or password.", 401)
    if user.status != "approved":
        raise AppError("FORBIDDEN", "Your account is waiting for admin approval.", 403)
    return user


def register(name, email, password, role):
    """Create a pending student or staff account (US1)."""
    return _create_user(name, email, password, role=role, status="pending")


def create_admin(name, email, password):
    """Create an approved admin account (T1-1). Only reachable from the CLI."""
    return _create_user(name, email, password, role="admin", status="approved")


def _create_user(name, email, password, role, status):
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
