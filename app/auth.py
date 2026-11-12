"""JWT helpers and the two access-control decorators.

Routes use them like this:

    @bp.get("/something")
    @token_required            # any logged-in, approved user
    def something(): ...

    @bp.post("/courses")
    @role_required("staff")    # logged in AND has one of these roles
    def create_course(): ...

The logged-in user is available as flask.g.current_user inside the view.
"""
from datetime import UTC, datetime, timedelta
from functools import wraps

import jwt
from flask import current_app, g, request

from .errors import AppError
from .extensions import db
from .models import User

ALGORITHM = "HS256"


def _secret():
    secret = current_app.config.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set. Add it to your .env file.")
    return secret


def create_access_token(user, expires_in=None):
    """Sign a token carrying the user's id, role, and expiry time."""
    lifetime = expires_in if expires_in is not None else current_app.config["JWT_EXPIRES_SECONDS"]
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def decode_access_token(token):
    """Return the token's claims, or raise AppError(UNAUTHORIZED, 401)."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AppError("UNAUTHORIZED", "Token has expired.", 401)
    except jwt.InvalidTokenError:
        raise AppError("UNAUTHORIZED", "Invalid token.", 401)


def _load_user(user_id):
    return db.session.get(User, user_id)


def token_required(view):
    """Allow the request only with a valid 'Authorization: Bearer <token>' header."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        token = token.strip()
        if scheme != "Bearer" or not token:
            raise AppError("UNAUTHORIZED", "Missing or malformed Authorization header.", 401)

        claims = decode_access_token(token)
        try:
            user = _load_user(int(claims["sub"]))
        except (KeyError, ValueError):
            user = None
        if user is None or user.status != "approved":
            raise AppError("UNAUTHORIZED", "Invalid token.", 401)

        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """Allow the request only for a logged-in user whose role is in roles."""

    def decorator(view):
        @wraps(view)
        @token_required
        def wrapper(*args, **kwargs):
            if g.current_user.role not in roles:
                raise AppError("FORBIDDEN", "You do not have permission to do this.", 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
