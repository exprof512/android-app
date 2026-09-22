"""Try multiple text providers in order (OpenAI → DeepSeek)."""

from __future__ import annotations

import logging

from app.ai.errors import TextAIProviderError
from app.ai.provider import TextGenerationProvider, TextGenerationRequest, TextGenerationResult

logger = logging.getLogger(__name__)

_FALLBACK_CODES = frozenset(
    {
        "ai_quota_exhausted",
        "ai_provider_error",
        "ai_provider_timeout",
        "ai_bad_request",
        "ai_empty_response",
        "ai_auth_error",
    }
)


class FallbackTextProvider:
    """Uses the first successful provider; never logs prompts or keys."""

    def __init__(self, providers: list[tuple[str, TextGenerationProvider]]) -> None:
        if not providers:
            raise ValueError("FallbackTextProvider requires at least one provider")
        self._providers = providers

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        last_error: TextAIProviderError | None = None
        for name, provider in self._providers:
            try:
                result = await provider.generate(request)
                if name != self._providers[0][0]:
                    logger.info(
                        "text_ai_fallback_provider_used",
                        extra={"provider": name, "operation": request.operation},
                    )
                return result
            except TextAIProviderError as exc:
                last_error = exc
                logger.warning(
                    "text_ai_provider_failed_trying_next",
                    extra={
                        "provider": name,
                        "error_code": exc.code,
                        "operation": request.operation,
                    },
                )
                if exc.code not in _FALLBACK_CODES:
                    raise
                continue
        assert last_error is not None
        raise last_error
