import os

from dotenv import load_dotenv

load_dotenv()


def _origins(value: str) -> list[str]:
    """'https://a.com, https://b.com' -> ['https://a.com', 'https://b.com']"""
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Config:
    """All settings come from environment variables (see .env.example)."""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    JWT_SECRET = os.environ.get("JWT_SECRET")
    JWT_EXPIRES_SECONDS = 3600

    # bcrypt work factor: each +1 doubles the time to hash (and to guess) a password.
    # 12 is bcrypt's own default. Tests lower it to 4 so the suite runs fast.
    BCRYPT_ROUNDS = 12

    # Login attempts allowed per client IP. Slows down password guessing.
    LOGIN_RATE_LIMIT = os.environ.get("LOGIN_RATE_LIMIT", "5 per minute")
    # Counts are kept in this process's memory; several server processes would
    # need a shared store such as Redis.
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    # DEBUG, INFO, WARNING, or ERROR.
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Browser front ends allowed to call this API. Empty means none.
    CORS_ORIGINS = _origins(os.environ.get("CORS_ORIGINS", ""))
