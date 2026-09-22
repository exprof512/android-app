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


def test_jwt_and_db_url_are_scrubbed_from_messages() -> None:
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "signaturepartgoesherelikereal"
    )
    record_message = (
        f"bad token {jwt} url postgresql+asyncpg://foodai:supersecret@postgres/foodai"
    )
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=record_message,
        args=(),
        exc_info=None,
    )
    payload = json.loads(JsonFormatter().format(record))
    assert "supersecret" not in payload["message"]
    assert "[REDACTED]" in payload["message"] or "[REDACTED_JWT]" in payload["message"]
    assert jwt not in payload["message"]


def test_health_includes_security_headers() -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    class HealthyServices:
        async def start(self) -> None:
            return None

        async def check_health(self) -> None:
            return None

        async def check_health_details(self) -> dict[str, str]:
            return {"postgres": "ok", "redis": "ok", "storage": "skipped"}

        async def close(self) -> None:
            return None

    app = create_app(
        Settings(
            app_env="test",
            database_url="postgresql+asyncpg://foodai:test@localhost/foodai",
            redis_url="redis://localhost:6379/0",
            jwt_secret="unit-test-signing-key-with-enough-entropy",
        )
    )
    app.state.services = HealthyServices()

    with TestClient(app) as client:
        response = client.get("/health")
        deps = client.get("/health/deps")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert deps.status_code == 200
    assert deps.json()["dependencies"]["postgres"] == "ok"


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
