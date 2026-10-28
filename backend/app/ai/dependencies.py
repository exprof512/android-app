"""Text AI FastAPI dependencies.

Phase 21 routing: DeepSeek is the exclusive product text provider.
OpenAI is never used for chat/plans/recipes/suggestions here.
"""

from __future__ import annotations

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import MemoryCacheStore, RedisCacheStore, TextAICache
from app.ai.fallback import FallbackTextProvider
from app.ai.mock import MockTextProvider
from app.ai.provider import TextGenerationProvider
from app.ai.service import TextAIService
from app.core.config import Settings
from app.core.dependencies import get_db_session, get_redis, get_services
from app.core.services import Services
from app.integrations.deepseek.text import DeepSeekChatProvider
from app.integrations.openai.text import OpenAIResponsesProvider


def build_text_provider(settings: Settings) -> TextGenerationProvider:
    """DeepSeek first; OpenAI Responses only as an explicit fallback.

    A revoked DeepSeek key used to disable chat and live plan generation while
    the OpenAI key was still valid. Keep DeepSeek as the primary provider and
    fall back on auth/quota/provider errors instead of failing the product.
    """
    providers: list[tuple[str, TextGenerationProvider]] = []
    if settings.deepseek_api_key.strip():
        providers.append(
            (
                "deepseek",
                DeepSeekChatProvider(
                    api_key=settings.deepseek_api_key,
                    model=settings.deepseek_text_model or "deepseek-chat",
                    timeout_seconds=settings.deepseek_text_timeout_seconds,
                    base_url=settings.deepseek_base_url or "https://api.deepseek.com",
                ),
            )
        )
    if settings.openai_api_key.strip():
        providers.append(
            (
                "openai",
                OpenAIResponsesProvider(
                    api_key=settings.openai_api_key,
                    model=settings.openai_text_model.strip() or "gpt-4.1-mini",
                    timeout_seconds=settings.openai_text_timeout_seconds,
                ),
            )
        )
    if not providers:
        return MockTextProvider(
            model=settings.deepseek_text_model or "mock-text-model"
        )
    if len(providers) == 1:
        return providers[0][1]
    return FallbackTextProvider(providers)


def get_text_provider(
    request: Request, services: Services = Depends(get_services)
) -> TextGenerationProvider:
    provider = getattr(request.app.state, "text_ai_provider", None)
    if provider is not None:
        return provider
    settings: Settings = request.app.state.settings
    if settings.app_env == "test":
        return MockTextProvider(model=settings.deepseek_text_model or "mock-text-model")
    if services.text_provider is None:
        services.text_provider = build_text_provider(settings)
    return services.text_provider


def get_text_ai_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    provider: TextGenerationProvider = Depends(get_text_provider),
) -> TextAIService:
    settings: Settings = request.app.state.settings
    store = getattr(request.app.state, "text_ai_cache_store", None)
    if store is None:
        if settings.app_env == "test":
            store = MemoryCacheStore()
            request.app.state.text_ai_cache_store = store
        else:
            store = RedisCacheStore(redis)
    cache = TextAICache(
        store,
        ttl_seconds=settings.ai_cache_ttl_seconds,
        schema_version=settings.openai_response_schema_version,
    )
    model_name = settings.deepseek_text_model or "deepseek-chat"
    return TextAIService(
        provider=provider,
        cache=cache,
        session=session,
        model=model_name,
        max_attempts=settings.openai_text_max_attempts,
        schema_version=settings.openai_response_schema_version,
    )
