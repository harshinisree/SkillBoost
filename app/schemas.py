from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

# bcrypt only uses the first 72 bytes of a password, so longer ones are rejected.
BCRYPT_MAX_BYTES = 72

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class AccountSchema(BaseModel):
    """Rules shared by every way of creating an account."""

    name: Name
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value):
        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError("password must be at most 72 bytes")
        return value


class RegisterSchema(AccountSchema):
    """Body of POST /auth/register. Admin is not an allowed role."""

    role: Literal["student", "staff"]


class LoginSchema(BaseModel):
    """Body of POST /auth/login. The email format is not checked here, so a
    malformed email gets the same 401 as any other wrong login."""

    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: str = Field(min_length=1)
