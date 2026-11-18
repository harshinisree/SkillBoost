"""T4-8: tests hash passwords cheaply, but the real app keeps full strength."""
import bcrypt

from app import create_app
from app.config import Config
from app.services.user_service import check_password, hash_password


def cost_of(password_hash):
    """bcrypt hashes look like $2b$12$...: the number is the cost."""
    return int(password_hash.split("$")[2])


def test_t4_8_the_real_app_uses_cost_12():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "JWT_SECRET": "unit-secret-0123456789abcdef"})

    assert Config.BCRYPT_ROUNDS == 12
    with app.app_context():
        assert cost_of(hash_password("StrongPass1")) == 12


def test_t4_8_outside_an_app_the_safe_default_is_used():
    assert cost_of(hash_password("StrongPass1")) == 12


def test_t4_8_the_test_app_uses_the_cheap_cost(app):
    with app.app_context():
        password_hash = hash_password("StrongPass1")

    assert cost_of(password_hash) == 4
    assert check_password("StrongPass1", password_hash)


def test_t4_8_hashes_of_any_cost_still_verify():
    # A database can hold hashes made with different costs; all must keep working.
    for rounds in (4, 12):
        password_hash = bcrypt.hashpw(b"StrongPass1", bcrypt.gensalt(rounds=rounds)).decode()
        assert check_password("StrongPass1", password_hash)
