"""Text AI FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import MemoryCacheStore, RedisCacheStore, TextAICache
from app.ai.mock import MockTextProvider
from app.ai.provider import TextGenerationProvider
from app.ai.service import TextAIService
from app.core.config import Settings
from app.core.dependencies import get_db_session, get_redis, get_services
from app.core.services import Services
from app.integrations.openai.text import OpenAIResponsesProvider


def get_text_provider(
    request: Request, services: Services = Depends(get_services)
) -> TextGenerationProvider:
    provider = getattr(request.app.state, "text_ai_provider", None)
    if provider is not None:
        return provider
    settings: Settings = request.app.state.settings
    if settings.app_env == "test" or not settings.openai_api_key.strip():
        # Live provider is opt-in via OPENAI_API_KEY; tests inject MockTextProvider.
        return MockTextProvider(model=settings.openai_text_model or "mock-text-model")
    if services.text_provider is None:
        services.text_provider = OpenAIResponsesProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_text_model or "gpt-4.1-mini",
            timeout_seconds=settings.openai_text_timeout_seconds,
        )
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
    return TextAIService(
        provider=provider,
        cache=cache,
        session=session,
        model=settings.openai_text_model or "gpt-4.1-mini",
        max_attempts=settings.openai_text_max_attempts,
        schema_version=settings.openai_response_schema_version,
    )
