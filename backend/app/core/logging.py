"""JSON logging with defensive redaction."""

from __future__ import annotations

import json
import logging
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
)


def _redact(value: Any, key: str = "") -> Any:
    if any(marker in key.lower() for marker in _SENSITIVE_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _redact(item, str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item, key) for item in value]
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
