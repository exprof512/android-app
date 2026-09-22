"""Fallback text provider unit tests — no network."""

from __future__ import annotations

import pytest

from app.ai.errors import TextAIProviderError
from app.ai.fallback import FallbackTextProvider
from app.ai.provider import TextGenerationRequest, TextGenerationResult


class _Failing:
    def __init__(self, code: str) -> None:
        self.code = code

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        raise TextAIProviderError(code=self.code, message="fail", retryable=False)


class _Ok:
    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        return TextGenerationResult(
            content='{"ok":true}',
            model="deepseek-chat",
            input_tokens=1,
            output_tokens=1,
            duration_ms=1,
        )


@pytest.mark.asyncio
async def test_fallback_uses_second_provider_after_quota():
    chain = FallbackTextProvider(
        [
            ("openai", _Failing("ai_quota_exhausted")),
            ("deepseek", _Ok()),
        ]
    )
    result = await chain.generate(
        TextGenerationRequest(
            operation="generate_meal_plan_proposal",
            schema_name="generate_meal_plan_proposal",
            json_schema={"type": "object"},
            system_prompt="sys",
            user_payload={},
        )
    )
    assert result.model == "deepseek-chat"
    assert "ok" in result.content


@pytest.mark.asyncio
async def test_fallback_raises_when_all_fail():
    chain = FallbackTextProvider(
        [
            ("openai", _Failing("ai_quota_exhausted")),
            ("deepseek", _Failing("ai_provider_error")),
        ]
    )
    with pytest.raises(TextAIProviderError) as exc:
        await chain.generate(
            TextGenerationRequest(
                operation="generate_meal_plan_proposal",
                schema_name="generate_meal_plan_proposal",
                json_schema={"type": "object"},
                system_prompt="sys",
                user_payload={},
            )
        )
    assert exc.value.code == "ai_provider_error"
