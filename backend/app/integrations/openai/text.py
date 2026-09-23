"""OpenAI Responses API text provider with Structured Outputs."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import APITimeoutError, AsyncOpenAI, OpenAIError

from app.ai.errors import TextAIProviderError
from app.ai.provider import TextGenerationRequest, TextGenerationResult
from app.integrations.openai.client import create_openai_client
from app.integrations.openai.errors import classify_openai_error

logger = logging.getLogger(__name__)


class OpenAIResponsesProvider:
    """Calls the Responses API; never logs prompts, keys, or full profiles."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI | None = None,
        api_key: str = "",
        model: str,
        timeout_seconds: float = 30,
    ) -> None:
        self._model = model
        self._client = client or create_openai_client(
            api_key=api_key, timeout_seconds=timeout_seconds
        )

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        started = time.perf_counter()
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": request.system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(
                                    request.user_payload, ensure_ascii=False
                                ),
                            }
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": request.schema_name,
                        "strict": True,
                        "schema": request.json_schema,
                    }
                },
            )
        except APITimeoutError as exc:
            raise TextAIProviderError(
                code="ai_provider_timeout",
                message="AI provider timed out.",
                retryable=True,
            ) from exc
        except OpenAIError as exc:
            code, message, retryable = classify_openai_error(exc)
            payload = getattr(exc, "body", None)
            err = payload.get("error") if isinstance(payload, dict) else None
            logger.warning(
                "openai_text_provider_error",
                extra={
                    "error_code": code,
                    "operation": request.operation,
                    "http_status": getattr(exc, "status_code", None),
                    "openai_param": (
                        err.get("param") if isinstance(err, dict) else None
                    ),
                    "openai_api_code": (
                        err.get("code") if isinstance(err, dict) else None
                    ),
                },
            )
            raise TextAIProviderError(
                code=code,
                message=message,
                retryable=retryable,
            ) from exc

        content = _extract_output_text(response)
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        duration_ms = int((time.perf_counter() - started) * 1000)
        return TextGenerationResult(
            content=content,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            raw_response_id=getattr(response, "id", None),
        )


def _extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                chunks.append(part_text)
    joined = "".join(chunks).strip()
    if not joined:
        raise TextAIProviderError(
            code="ai_empty_response",
            message="AI provider returned an empty response.",
            retryable=True,
        )
    return joined
