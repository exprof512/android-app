"""TextAIService: structured generation with repair, cache and usage audit."""

from __future__ import annotations

import json
import logging
import time
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import TextAICache
from app.ai.errors import TextAIProviderError, TextAIUnavailable, TextAIValidationFailed
from app.ai.models import AiTextUsage
from app.ai.prompts import system_prompt_for
from app.ai.provider import TextGenerationProvider, TextGenerationRequest
from app.ai.schemas import (
    ChatAnswerResponse,
    MealPlanProposalResponse,
    OPERATION_SCHEMAS,
    RecipeCandidatesResponse,
    ReplaceMealResponse,
    json_schema_for,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Rough USD estimate for audit only; not billing.
_INPUT_COST_PER_1K = Decimal("0.00015")
_OUTPUT_COST_PER_1K = Decimal("0.0006")


class TextAIService:
    """Application-facing text AI. Domain engines still own persistence and math."""

    def __init__(
        self,
        *,
        provider: TextGenerationProvider,
        cache: TextAICache,
        session: AsyncSession,
        model: str,
        max_attempts: int = 2,
        schema_version: int = 1,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._session = session
        self._model = model
        self._max_attempts = max(1, max_attempts)
        self._schema_version = schema_version

    async def generate_recipe_candidates(
        self,
        *,
        context: dict[str, Any],
        user_id: UUID | None = None,
        use_cache: bool = True,
    ) -> RecipeCandidatesResponse:
        return await self._run(
            operation="generate_recipe_candidates",
            model_type=RecipeCandidatesResponse,
            context=context,
            user_id=user_id,
            use_cache=use_cache,
        )

    async def generate_meal_plan_proposal(
        self,
        *,
        context: dict[str, Any],
        user_id: UUID | None = None,
        use_cache: bool = True,
    ) -> MealPlanProposalResponse:
        return await self._run(
            operation="generate_meal_plan_proposal",
            model_type=MealPlanProposalResponse,
            context=context,
            user_id=user_id,
            use_cache=use_cache,
        )

    async def replace_meal_item(
        self,
        *,
        context: dict[str, Any],
        user_id: UUID | None = None,
        use_cache: bool = False,
    ) -> ReplaceMealResponse:
        return await self._run(
            operation="replace_meal_item",
            model_type=ReplaceMealResponse,
            context=context,
            user_id=user_id,
            use_cache=use_cache,
        )

    async def chat_answer(
        self,
        *,
        context: dict[str, Any],
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        use_cache: bool = False,
    ) -> ChatAnswerResponse:
        return await self._run(
            operation="chat_answer",
            model_type=ChatAnswerResponse,
            context=context,
            user_id=user_id,
            conversation_id=conversation_id,
            use_cache=use_cache,
        )

    async def _run(
        self,
        *,
        operation: str,
        model_type: type[T],
        context: dict[str, Any],
        user_id: UUID | None,
        conversation_id: UUID | None = None,
        use_cache: bool,
    ) -> T:
        if operation not in OPERATION_SCHEMAS:
            raise TextAIUnavailable()

        fingerprint = self._cache.fingerprint(
            operation=operation, model=self._model, payload=context
        )
        if use_cache:
            cached = await self._cache.get(fingerprint)
            if cached is not None:
                parsed = model_type.model_validate(cached)
                await self._record_usage(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    operation=operation,
                    status="cached",
                    duration_ms=0,
                    fingerprint=fingerprint,
                )
                return parsed

        last_error: Exception | None = None
        repair_hint: str | None = None
        for attempt in range(1, self._max_attempts + 1):
            payload = dict(context)
            if repair_hint:
                payload["validation_feedback"] = repair_hint
            request = TextGenerationRequest(
                operation=operation,
                schema_name=operation,
                json_schema=json_schema_for(operation),
                system_prompt=system_prompt_for(operation),
                user_payload=payload,
            )
            started = time.perf_counter()
            try:
                result = await self._provider.generate(request)
            except TextAIProviderError as exc:
                last_error = exc
                await self._record_usage(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    operation=operation,
                    status="failed",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    fingerprint=fingerprint,
                    error_code=exc.code,
                    model=self._model,
                )
                if not exc.retryable or attempt >= self._max_attempts:
                    raise TextAIUnavailable() from exc
                continue

            try:
                data = json.loads(result.content)
                parsed = model_type.model_validate(data)
            except (json.JSONDecodeError, ValidationError, TypeError) as exc:
                last_error = exc
                repair_hint = _safe_validation_feedback(exc)
                await self._record_usage(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    operation=operation,
                    status="invalid",
                    duration_ms=result.duration_ms,
                    fingerprint=fingerprint,
                    error_code="ai_output_invalid",
                    model=result.model,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                )
                logger.info(
                    "ai_text_schema_repair",
                    extra={
                        "operation": operation,
                        "attempt": attempt,
                        "error_code": "ai_output_invalid",
                    },
                )
                continue

            await self._record_usage(
                user_id=user_id,
                conversation_id=conversation_id,
                operation=operation,
                status="ok",
                duration_ms=result.duration_ms,
                fingerprint=fingerprint,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost=_estimate_cost(result.input_tokens, result.output_tokens),
            )
            if use_cache:
                await self._cache.set(fingerprint, parsed.model_dump(mode="json"))
            return parsed

        if isinstance(last_error, ValidationError):
            raise TextAIValidationFailed() from last_error
        raise TextAIUnavailable() from last_error

    async def _record_usage(
        self,
        *,
        user_id: UUID | None,
        conversation_id: UUID | None,
        operation: str,
        status: str,
        duration_ms: int,
        fingerprint: str,
        error_code: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost: Decimal | None = None,
    ) -> None:
        self._session.add(
            AiTextUsage(
                user_id=user_id,
                conversation_id=conversation_id,
                operation=operation,
                model=model or self._model or "unknown",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=estimated_cost,
                status=status,
                duration_ms=duration_ms,
                error_code=error_code,
                request_fingerprint=fingerprint,
                schema_version=self._schema_version,
            )
        )
        await self._session.flush()


def _estimate_cost(input_tokens: int | None, output_tokens: int | None) -> Decimal | None:
    if input_tokens is None and output_tokens is None:
        return None
    inp = Decimal(input_tokens or 0) / Decimal(1000) * _INPUT_COST_PER_1K
    out = Decimal(output_tokens or 0) / Decimal(1000) * _OUTPUT_COST_PER_1K
    return (inp + out).quantize(Decimal("0.000001"))


def _safe_validation_feedback(exc: Exception) -> str:
    """Feedback for repair retry without dumping full PII context."""
    if isinstance(exc, ValidationError):
        parts = []
        for error in exc.errors()[:8]:
            field = ".".join(str(part) for part in error.get("loc", ()))
            parts.append(f"{field}:{error.get('type')}")
        return "Fix schema issues: " + "; ".join(parts)
    if isinstance(exc, json.JSONDecodeError):
        return "Response must be valid JSON matching the schema."
    return "Response must match the required JSON schema."
