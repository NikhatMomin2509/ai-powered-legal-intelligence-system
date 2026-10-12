"""
schemas/auth.py — Pydantic models for register/login/me.

Password minimum length is enforced here (8 chars) — deliberately simple,
not a full complexity-rules policy, which would be disproportionate for an
academic project. Email format is validated by Pydantic's EmailStr.

Password MAX length (72 bytes) is not arbitrary: bcrypt silently ignores
any bytes past the 72nd when hashing — without this cap, two different long
passwords sharing the same first 72 bytes would hash identically, a real,
if obscure, correctness issue worth guarding against explicitly.
"""

from pydantic import BaseModel, EmailStr, field_validator

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt's hard limit


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_length_bounds(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
