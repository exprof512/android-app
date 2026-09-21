"""In-memory TextGenerationProvider for unit tests — never calls OpenAI."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

from app.ai.errors import TextAIProviderError
from app.ai.provider import TextGenerationRequest, TextGenerationResult


class MockTextProvider:
    """Queue of scripted responses; supports malformed JSON and provider errors."""

    def __init__(
        self,
        responses: Sequence[str | dict[str, Any] | Exception | Callable[[], Any]] | None = None,
        *,
        model: str = "mock-text-model",
    ) -> None:
        self._responses = list(responses or [])
        self._model = model
        self.calls: list[TextGenerationRequest] = []

    def enqueue(self, *items: str | dict[str, Any] | Exception | Callable[[], Any]) -> None:
        self._responses.extend(items)

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.calls.append(request)
        if not self._responses:
            raise TextAIProviderError(
                code="ai_provider_error",
                message="Mock provider has no queued responses.",
                retryable=False,
            )
        item = self._responses.pop(0)
        if callable(item):
            item = item()
        if isinstance(item, Exception):
            raise item
        if isinstance(item, dict):
            content = json.dumps(item, ensure_ascii=False)
        else:
            content = str(item)
        return TextGenerationResult(
            content=content,
            model=self._model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=5,
            raw_response_id="mock-response",
        )
