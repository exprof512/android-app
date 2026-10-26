"""Keep .env.example in sync with Settings so deployments do not drift."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import Settings

# Documented for Docker Compose only, not read by Settings.
COMPOSE_ONLY_KEYS = {
    "postgres_user",
    "postgres_db",
    "postgres_password",
    "redis_password",
    "nginx_port",
}


def _resolve_env_example() -> Path | None:
    override = os.environ.get("FOODAI_ENV_EXAMPLE")
    if override:
        candidate = Path(override)
        return candidate if candidate.is_file() else None
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env.example"
        if candidate.is_file():
            return candidate
    candidate = Path.cwd().parent / ".env.example"
    return candidate if candidate.is_file() else None


ENV_EXAMPLE = _resolve_env_example()
pytestmark = pytest.mark.skipif(
    ENV_EXAMPLE is None,
    reason=".env.example is not mounted; run from a repository checkout",
)


def _documented_keys() -> set[str]:
    assert ENV_EXAMPLE is not None
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        keys.add(entry.split("=", 1)[0].strip().lower())
    return keys


def test_every_setting_is_documented_in_env_example() -> None:
    missing = sorted(set(Settings.model_fields) - _documented_keys())
    assert missing == [], f"not documented in .env.example: {missing}"


def test_env_example_has_no_unknown_settings() -> None:
    extra = sorted(
        _documented_keys() - set(Settings.model_fields) - COMPOSE_ONLY_KEYS
    )
    assert extra == [], f"unknown keys in .env.example: {extra}"
