import bcrypt
import pytest
from pydantic import ValidationError

from app.schemas import RegisterSchema
from app.services.user_service import hash_password

VALID = {
    "name": "Asha Rao",
    "email": "asha@example.com",
    "password": "StrongPass1",
    "role": "student",
}


def test_us1_schema_accepts_valid_input():
    data = RegisterSchema.model_validate(VALID)

    assert data.role == "student"


def test_us1_schema_lowercases_email():
    data = RegisterSchema.model_validate({**VALID, "email": "Asha@Example.COM"})

    assert data.email == "asha@example.com"


def test_us1_schema_trims_name_but_not_password():
    data = RegisterSchema.model_validate(
        {**VALID, "name": "  Asha Rao  ", "password": "  spaced pass  "}
    )

    assert data.name == "Asha Rao"
    assert data.password == "  spaced pass  "


def test_us1_schema_rejects_admin_role():
    with pytest.raises(ValidationError):
        RegisterSchema.model_validate({**VALID, "role": "admin"})


def test_us1_schema_rejects_password_longer_than_72_bytes():
    # 40 two-byte characters = 80 bytes, which bcrypt cannot use in full.
    with pytest.raises(ValidationError):
        RegisterSchema.model_validate({**VALID, "password": "é" * 40})


def test_us1_hash_password_is_salted_and_verifies():
    first = hash_password("StrongPass1")
    second = hash_password("StrongPass1")

    assert first != second
    assert first != "StrongPass1"
    assert bcrypt.checkpw(b"StrongPass1", first.encode("utf-8"))
