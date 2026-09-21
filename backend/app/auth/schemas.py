"""Request and response contracts for auth and current user."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

Password = Annotated[
    str, Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
]
Email = Annotated[EmailStr, Field(max_length=320)]


class RegisterRequest(BaseModel):
    email: Email
    password: Password
    locale: str = Field(default="ru-RU", max_length=16)
    accepted_terms_at: datetime | None = None

    @field_validator("password")
    @classmethod
    def password_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must_not_be_blank")
        return value


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class UserSummary(BaseModel):
    id: UUID
    email: EmailStr
    tier: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    tier: str
    locale: str
    is_active: bool
    accepted_terms_at: datetime | None
    created_at: datetime
