"""JSON logging with defensive redaction."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

_SENSITIVE_MARKERS = (
    "authorization",
    "cookie",
    "credential",
    "database_url",
    "password",
    "secret",
    "token",
    "api_key",
    "access_key",
    "secret_key",
    "refresh",
    "bearer",
    "openai",
    "deepseek",
    "presigned",
    "signed_url",
    "private_key",
)
_SAFE_FIELDS = (
    "request_id",
    "user_id",
    "endpoint",
    "method",
    "status_code",
    "duration_ms",
    "ai_duration_ms",
    "image_duration_ms",
    "error_code",
    "job_id",
    "recipe_id",
    "recipe_image_id",
    "detail_count",
)

_JWT_LIKE = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
)
_URL_WITH_CREDS = re.compile(r"(://[^:/@\s]+):([^@/\s]+)@")
_CONN_PASSWORD = re.compile(
    r"(postgres(?:ql)?(?:\+asyncpg)?://[^:]+:)([^@]+)(@)",
    flags=re.IGNORECASE,
)


def redact_text(value: str) -> str:
    """Scrub secret-looking substrings from free-form log messages."""
    scrubbed = _JWT_LIKE.sub("[REDACTED_JWT]", value)
    scrubbed = _URL_WITH_CREDS.sub(r"\1[REDACTED]@", scrubbed)
    scrubbed = _CONN_PASSWORD.sub(r"\1[REDACTED]\3", scrubbed)
    return scrubbed


def _redact(value: Any, key: str = "") -> Any:
    if any(marker in key.lower() for marker in _SENSITIVE_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _redact(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item, key) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage(), "message"),
        }
        for field in _SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = _redact(value, field)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())
