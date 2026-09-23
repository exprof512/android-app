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
    platform: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=32)
    device_label: str | None = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def password_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must_not_be_blank")
        return value


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    platform: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=32)
    device_label: str | None = Field(default=None, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=8, max_length=512)


class ResendVerificationRequest(BaseModel):
    email: Email


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    new_password: Password

    @field_validator("new_password")
    @classmethod
    def password_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must_not_be_blank")
        return value


class GenericMessageResponse(BaseModel):
    message: str


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


class ConsentState(BaseModel):
    terms_version: str | None
    privacy_version: str | None
    accepted_terms_at: datetime | None
    terms_url: str
    privacy_url: str


class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    tier: str
    locale: str
    is_active: bool
    role: str
    email_verified: bool
    email_verified_at: datetime | None
    accepted_terms_at: datetime | None
    terms_version: str | None
    privacy_version: str | None
    consent: ConsentState
    created_at: datetime


class SessionOut(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    device_label: str | None
    platform: str | None
    app_version: str | None
    is_current: bool


class ListSessionsRequest(BaseModel):
    current_refresh_token: str | None = Field(default=None, max_length=4096)


class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=32)

    @field_validator("confirmation")
    @classmethod
    def must_be_delete(cls, value: str) -> str:
        if value.strip().upper() != "DELETE":
            raise ValueError("must_equal_DELETE")
        return "DELETE"
