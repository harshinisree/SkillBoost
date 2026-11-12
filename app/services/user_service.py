import bcrypt
from sqlalchemy.exc import IntegrityError

from ..errors import AppError
from ..extensions import db
from ..models import User


def hash_password(password):
    """Return a salted bcrypt hash of the password, as text."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def register(name, email, password, role):
    """Create a pending account. Raises AppError(EMAIL_TAKEN, 409) on a duplicate."""
    email = email.lower()
    taken = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if taken is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status="pending",
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Two requests with the same email raced; the UNIQUE constraint caught it.
        db.session.rollback()
        raise AppError("EMAIL_TAKEN", "An account with this email already exists.", 409)
    return user
