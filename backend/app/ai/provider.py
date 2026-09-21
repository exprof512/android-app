"""Typed boundary between TextAIService and OpenAI/mock providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TextGenerationRequest:
    operation: str
    schema_name: str
    json_schema: dict[str, Any]
    system_prompt: str
    user_payload: dict[str, Any]


@dataclass(frozen=True)
class TextGenerationResult:
    content: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int = 0
    raw_response_id: str | None = None


class TextGenerationProvider(Protocol):
    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult: ...
