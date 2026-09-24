"""OpenAI Vision provider — food photo analysis only."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Protocol

from openai import APITimeoutError, AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

from app.ai.errors import TextAIProviderError
from app.integrations.openai.client import create_openai_client
from app.integrations.openai.errors import classify_openai_error

logger = logging.getLogger(__name__)


class VisionFoodItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    estimated_grams: float | None = Field(default=None, gt=0, le=5000)
    confidence: float = Field(ge=0, le=1)
    notes: str | None = Field(default=None, max_length=500)


class VisionFoodAnalysisResult(BaseModel):
    items: list[VisionFoodItem] = Field(default_factory=list, max_length=20)
    overall_confidence: float = Field(default=0.0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    model: str = ""
    duration_ms: int = 0


class VisionAnalysisRequest(BaseModel):
    """In-memory request; never persisted or logged as raw bytes."""

    image_bytes: bytes
    mime_type: str = "image/jpeg"
    locale: str = "ru"


class VisionProvider(Protocol):
    async def analyze_food(self, request: VisionAnalysisRequest) -> VisionFoodAnalysisResult: ...


_VISION_SYSTEM = (
    "You identify foods in a meal photo for a nutrition app. "
    "Return JSON only with keys: items (array of {name, estimated_grams, confidence, notes}), "
    "overall_confidence (0-1), warnings (string array). "
    "Use common food names (Russian preferred when locale=ru). "
    "estimated_grams is approximate edible portion; null if unknown. "
    "Do not invent brands. Do not output calories or macros. "
    "confidence < 0.5 means uncertain."
)

_VISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "estimated_grams": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "notes": {"type": ["string", "null"]},
                },
                "required": ["name", "estimated_grams", "confidence", "notes"],
            },
        },
        "overall_confidence": {"type": "number"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["items", "overall_confidence", "warnings"],
}


class OpenAIVisionProvider:
    """ChatGPT/OpenAI vision for food photos. Never used for product text AI."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI | None = None,
        api_key: str = "",
        model: str = "gpt-4.1-mini",
        timeout_seconds: float = 60,
    ) -> None:
        self._model = model
        self._client = client or create_openai_client(
            api_key=api_key, timeout_seconds=timeout_seconds
        )

    async def analyze_food(
        self, request: VisionAnalysisRequest
    ) -> VisionFoodAnalysisResult:
        started = time.perf_counter()
        b64 = base64.b64encode(request.image_bytes).decode("ascii")
        data_url = f"data:{request.mime_type};base64,{b64}"
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": _VISION_SYSTEM}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(
                                    {"locale": request.locale, "task": "food_photo_analysis"},
                                    ensure_ascii=False,
                                ),
                            },
                            {"type": "input_image", "image_url": data_url},
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "food_photo_analysis",
                        "strict": True,
                        "schema": _VISION_SCHEMA,
                    }
                },
            )
        except APITimeoutError as exc:
            raise TextAIProviderError(
                code="ai_provider_timeout",
                message="Vision provider timed out.",
                retryable=True,
            ) from exc
        except OpenAIError as exc:
            code, message, retryable = classify_openai_error(exc)
            logger.warning(
                "openai_vision_provider_error",
                extra={
                    "error_code": code,
                    "operation": "food_photo_analysis",
                    "http_status": getattr(exc, "status_code", None),
                },
            )
            raise TextAIProviderError(code=code, message=message, retryable=retryable) from exc

        content = _extract_output_text(response)
        try:
            data = json.loads(content)
            parsed = VisionFoodAnalysisResult.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise TextAIProviderError(
                code="ai_output_invalid",
                message="Vision returned invalid JSON.",
                retryable=True,
            ) from exc

        parsed.model = self._model
        parsed.duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "openai_vision_ok",
            extra={
                "operation": "food_photo_analysis",
                "model": self._model,
                "duration_ms": parsed.duration_ms,
                "item_count": len(parsed.items),
            },
        )
        return parsed


class MockOpenAIVisionProvider:
    """Deterministic vision mock for pytest — no network."""

    def __init__(
        self,
        responses: list[VisionFoodAnalysisResult] | None = None,
        *,
        model: str = "mock-vision-model",
    ) -> None:
        self._queue = list(responses or [])
        self.calls: list[VisionAnalysisRequest] = []
        self._model = model

    def enqueue(self, result: VisionFoodAnalysisResult) -> None:
        self._queue.append(result)

    async def analyze_food(
        self, request: VisionAnalysisRequest
    ) -> VisionFoodAnalysisResult:
        self.calls.append(request)
        if not self._queue:
            raise TextAIProviderError(
                code="ai_empty_response",
                message="Mock vision queue empty.",
                retryable=False,
            )
        result = self._queue.pop(0)
        result.model = result.model or self._model
        result.duration_ms = result.duration_ms or 1
        return result


def _extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    # Fallback walk
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            value = getattr(content, "text", None)
            if isinstance(value, str):
                chunks.append(value)
    joined = "".join(chunks).strip()
    if not joined:
        raise TextAIProviderError(
            code="ai_empty_response",
            message="Vision provider returned empty content.",
            retryable=True,
        )
    return joined
