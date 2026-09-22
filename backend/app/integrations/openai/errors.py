"""Classify OpenAI text errors and extract safe provider codes."""

from __future__ import annotations

from typing import Any

from openai import APIStatusError, OpenAIError


def classify_openai_error(exc: OpenAIError) -> tuple[str, str, bool]:
    """Return (code, message, retryable) without leaking secrets."""
    status = getattr(exc, "status_code", None)
    payload = _error_payload(exc)
    api_code = str(payload.get("code") or "").lower()
    api_type = str(payload.get("type") or "").lower()
    blob = " ".join(
        str(payload.get(key) or "")
        for key in ("code", "type", "message", "param")
    ).lower()
    blob = f"{blob} {exc!s}".lower()

    if (
        status == 429
        or api_code in {"insufficient_quota", "credit_balance_exhausted"}
        or api_type in {"insufficient_quota", "insufficient_quota_error"}
        or "insufficient_quota" in blob
        or "credit_balance_exhausted" in blob
        or "billing" in blob and "hard_limit" in blob
    ):
        return (
            "ai_quota_exhausted",
            "На аккаунте OpenAI закончились кредиты. Пополните баланс или используйте fallback.",
            False,
        )
    if status in {401, 403}:
        return ("ai_auth_error", "AI provider rejected the API key.", False)
    if status == 400:
        return ("ai_bad_request", "AI provider rejected the request.", False)
    if isinstance(exc, APIStatusError) and status is not None and status >= 500:
        return ("ai_provider_error", "AI provider is temporarily unavailable.", True)
    return ("ai_provider_error", "AI provider is temporarily unavailable.", True)


def _error_payload(exc: OpenAIError) -> dict[str, Any]:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        return err if isinstance(err, dict) else body
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            data = response.json()
            if isinstance(data, dict):
                err = data.get("error")
                return err if isinstance(err, dict) else data
        except Exception:
            return {}
    return {}
