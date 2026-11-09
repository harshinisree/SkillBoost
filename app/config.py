import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """All settings come from environment variables (see .env.example)."""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    JWT_SECRET = os.environ.get("JWT_SECRET")
