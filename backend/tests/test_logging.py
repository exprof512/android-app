from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.core.services import Services


def format_record(**extra: object) -> dict:
    record = logging.LogRecord(
        name="app.auth.service",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="user_logged_in",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


def test_only_whitelisted_fields_reach_the_log() -> None:
    user_id = str(uuid4())

    payload = format_record(
        user_id=user_id,
        error_code="invalid_token",
        password="correct horse battery staple",
        access_token="eyJhbGciOiJIUzI1NiJ9.payload.signature",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$salt$hash",
    )

    assert payload["user_id"] == user_id
    assert payload["error_code"] == "invalid_token"
    assert "password" not in payload
    assert "access_token" not in payload
    assert "password_hash" not in payload


def test_sensitive_values_inside_allowed_fields_are_redacted() -> None:
    payload = format_record(error_code={"authorization": "Bearer eyJ", "kind": "safe"})

    assert payload["error_code"] == {"authorization": "[REDACTED]", "kind": "safe"}


@pytest.mark.parametrize("secret", ["CHANGE_ME", "too-short-secret"])
def test_weak_jwt_secret_fails_startup_outside_local_environments(secret: str) -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://foodai:test@postgres/foodai",
        redis_url="redis://redis:6379/0",
        jwt_secret=secret,
    )

    assert settings.weak_runtime_settings() == ("JWT_SECRET",)
    with pytest.raises(RuntimeError) as error:
        Services.from_settings(settings)

    assert secret not in str(error.value)


def test_missing_jwt_secret_fails_startup() -> None:
    settings = Settings(
        app_env="development",
        database_url="postgresql+asyncpg://foodai:test@postgres/foodai",
        redis_url="redis://redis:6379/0",
        jwt_secret="",
    )

    assert settings.required_runtime_settings() == ("JWT_SECRET",)
    with pytest.raises(RuntimeError):
        Services.from_settings(settings)
