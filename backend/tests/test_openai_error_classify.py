"""OpenAI error classification tests — no network."""

from __future__ import annotations

from types import SimpleNamespace

from app.integrations.openai.errors import classify_openai_error


def test_classify_credit_balance_exhausted_on_400():
    exc = SimpleNamespace(
        status_code=400,
        body={
            "error": {
                "message": "You exceeded your current quota",
                "type": "insufficient_quota",
                "code": "credit_balance_exhausted",
            }
        },
        response=None,
    )
    code, _message, retryable = classify_openai_error(exc)  # type: ignore[arg-type]
    assert code == "ai_quota_exhausted"
    assert retryable is False


def test_classify_generic_400():
    exc = SimpleNamespace(
        status_code=400,
        body={"error": {"message": "bad schema", "code": "invalid_request"}},
        response=None,
    )
    code, _message, retryable = classify_openai_error(exc)  # type: ignore[arg-type]
    assert code == "ai_bad_request"
    assert retryable is False
