"""OpenAI Images API provider."""

from __future__ import annotations

import base64
import logging
import time

from openai import APIStatusError, APITimeoutError, AsyncOpenAI, BadRequestError, OpenAIError

from app.images.errors import ImageProviderError
from app.images.schemas import ImageGenerationRequest, ImageGenerationResult
from app.integrations.openai.client import create_openai_client
from app.integrations.openai.image_params import (
    build_images_generate_params,
    resolve_image_settings,
)

logger = logging.getLogger(__name__)


class OpenAIImageProvider:
    def __init__(
        self,
        *,
        client: AsyncOpenAI | None = None,
        api_key: str = "",
        timeout_seconds: float = 90,
    ) -> None:
        self._client = client or create_openai_client(
            api_key=api_key, timeout_seconds=timeout_seconds
        )

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = time.perf_counter()
        resolved = resolve_image_settings(
            model=request.model,
            size=request.size,
            quality=request.quality,
            storage_format=request.storage_format,
            provider_format=request.provider_format,
        )
        params = build_images_generate_params(
            prompt=request.prompt,
            settings=resolved,
        )

        try:
            response = await self._client.images.generate(**params)
        except APITimeoutError as exc:
            raise ImageProviderError(
                code="ai_provider_timeout",
                message="Image provider timed out.",
                retryable=True,
            ) from exc
        except BadRequestError as exc:
            code, param = _openai_error_bits(exc)
            logger.warning(
                "openai_image_bad_request",
                extra={
                    "error_code": code or "ai_provider_bad_request",
                    "openai_param": param,
                    "image_model": resolved.model,
                    "image_size": resolved.size,
                    "image_quality": resolved.quality,
                    "image_provider_format": resolved.provider_format,
                },
            )
            raise ImageProviderError(
                code="ai_provider_bad_request",
                message="Image provider rejected the request.",
                retryable=False,
            ) from exc
        except APIStatusError as exc:
            retryable = exc.status_code in {408, 409, 429, 500, 502, 503, 504}
            logger.warning(
                "openai_image_provider_error",
                extra={
                    "error_code": "ai_provider_error",
                    "http_status": exc.status_code,
                    "image_model": resolved.model,
                },
            )
            raise ImageProviderError(
                code="ai_provider_error",
                message="Image provider is temporarily unavailable.",
                retryable=retryable,
            ) from exc
        except OpenAIError as exc:
            logger.warning(
                "openai_image_provider_error",
                extra={"error_code": "ai_provider_error", "image_model": resolved.model},
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
            model=resolved.model,
            duration_ms=int((time.perf_counter() - started) * 1000),
            revised_prompt=getattr(data, "revised_prompt", None),
        )


def _openai_error_bits(exc: APIStatusError) -> tuple[str | None, str | None]:
    """Extract safe error.code / error.param without logging prompt or keys."""
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None, None
    err = body.get("error")
    if not isinstance(err, dict):
        return None, None
    code = err.get("code")
    param = err.get("param")
    return (
        str(code) if code is not None else None,
        str(param) if param is not None else None,
    )
