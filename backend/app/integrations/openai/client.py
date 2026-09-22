"""OpenAI SDK boundary — the only package that imports the OpenAI client."""

from __future__ import annotations

from openai import AsyncOpenAI


def create_openai_client(
    *,
    api_key: str,
    timeout_seconds: float,
    base_url: str | None = None,
) -> AsyncOpenAI:
    """Build a shared async client. Callers must not log the key."""
    if not api_key.strip():
        raise RuntimeError("API key is required for the live text provider")
    kwargs: dict = {"api_key": api_key, "timeout": timeout_seconds}
    if base_url and base_url.strip():
        kwargs["base_url"] = base_url.strip()
    return AsyncOpenAI(**kwargs)
