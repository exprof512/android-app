"""DeepSeek text provider via OpenAI-compatible Chat Completions + JSON mode."""

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

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekChatProvider:
    """Calls DeepSeek Chat Completions; never logs prompts or keys."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI | None = None,
        api_key: str = "",
        model: str,
        timeout_seconds: float = 60,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
    ) -> None:
        self._model = model
        self._client = client or create_openai_client(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            base_url=base_url or DEFAULT_DEEPSEEK_BASE_URL,
        )

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        started = time.perf_counter()
        system = (
            f"{request.system_prompt}\n\n"
            "Respond with a single JSON object only (no markdown). "
            f"JSON schema name={request.schema_name}: "
            f"{json.dumps(request.json_schema, ensure_ascii=False)}"
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": json.dumps(request.user_payload, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
        except APITimeoutError as exc:
            raise TextAIProviderError(
                code="ai_provider_timeout",
                message="DeepSeek provider timed out.",
                retryable=True,
            ) from exc
        except OpenAIError as exc:
            code, message, retryable = classify_openai_error(exc)
            logger.warning(
                "deepseek_text_provider_error",
                extra={
                    "error_code": code,
                    "operation": request.operation,
                    "http_status": getattr(exc, "status_code", None),
                },
            )
            raise TextAIProviderError(
                code=code,
                message=message,
                retryable=retryable,
            ) from exc

        content = _extract_message_content(response)
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        duration_ms = int((time.perf_counter() - started) * 1000)
        return TextGenerationResult(
            content=content,
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            raw_response_id=getattr(response, "id", None),
        )


def _extract_message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise TextAIProviderError(
            code="ai_empty_response",
            message="DeepSeek returned an empty response.",
            retryable=True,
        )
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message is not None else None
    if not isinstance(content, str) or not content.strip():
        raise TextAIProviderError(
            code="ai_empty_response",
            message="DeepSeek returned an empty response.",
            retryable=True,
        )
    return content.strip()
