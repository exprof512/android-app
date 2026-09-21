"""OpenAI Images API provider."""

from __future__ import annotations

import base64
import logging
import time

from openai import APITimeoutError, AsyncOpenAI, OpenAIError

from app.images.errors import ImageProviderError
from app.images.schemas import ImageGenerationRequest, ImageGenerationResult
from app.integrations.openai.client import create_openai_client

logger = logging.getLogger(__name__)


class OpenAIImageProvider:
    def __init__(
        self,
        *,
        client: AsyncOpenAI | None = None,
        api_key: str = "",
        timeout_seconds: float = 60,
    ) -> None:
        self._client = client or create_openai_client(
            api_key=api_key, timeout_seconds=timeout_seconds
        )

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = time.perf_counter()
        params: dict = {
            "model": request.model,
            "prompt": request.prompt,
            "n": 1,
        }
        # Only send supported optional knobs when configured.
        if request.size:
            params["size"] = request.size
        if request.quality:
            params["quality"] = request.quality
        if request.output_format:
            params["output_format"] = request.output_format

        try:
            response = await self._client.images.generate(**params)
        except APITimeoutError as exc:
            raise ImageProviderError(
                code="ai_provider_timeout",
                message="Image provider timed out.",
                retryable=True,
            ) from exc
        except OpenAIError as exc:
            logger.warning(
                "openai_image_provider_error",
                extra={"error_code": "ai_provider_error"},
            )
            raise ImageProviderError(
                code="ai_provider_error",
                message="Image provider is temporarily unavailable.",
                retryable=True,
            ) from exc

        data = (response.data or [None])[0]
        if data is None or not getattr(data, "b64_json", None):
            raise ImageProviderError(
                code="ai_empty_response",
                message="Image provider returned an empty response.",
                retryable=True,
            )
        content = base64.b64decode(data.b64_json)
        return ImageGenerationResult(
            content=content,
            model=request.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            revised_prompt=getattr(data, "revised_prompt", None),
        )
