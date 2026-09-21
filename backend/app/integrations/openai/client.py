"""OpenAI SDK boundary — the only package that imports the OpenAI client."""

from __future__ import annotations

from openai import AsyncOpenAI


def create_openai_client(*, api_key: str, timeout_seconds: float) -> AsyncOpenAI:
    """Build a shared async client. Callers must not log the key."""
    if not api_key.strip():
        raise RuntimeError("OPENAI_API_KEY is required for the live OpenAI provider")
    return AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
