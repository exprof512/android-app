"""Application infrastructure container."""

from __future__ import annotations

import asyncio
import logging

from app.ai.provider import TextGenerationProvider
from app.auth.passwords import PasswordHasher
from app.auth.tokens import TokenService
from app.core.config import Settings
from app.core.db import Database
from app.core.errors import DependencyUnavailable
from app.core.redis import RedisClient
from app.nutrition.engine import NutritionEngine

logger = logging.getLogger(__name__)

# Answer before the Docker/Nginx healthcheck gives up, so a stalled dependency
# surfaces as 503 instead of a hanging request.
HEALTHCHECK_TIMEOUT_SECONDS = 2.0


class Services:
    """Explicit dependency container shared by HTTP handlers."""

    def __init__(
        self,
        database: Database,
        redis: RedisClient,
        passwords: PasswordHasher,
        tokens: TokenService,
        nutrition: NutritionEngine,
        text_provider: TextGenerationProvider | None = None,
    ) -> None:
        self.database = database
        self.redis = redis
        self.passwords = passwords
        self.tokens = tokens
        self.nutrition = nutrition
        self.text_provider = text_provider

    @classmethod
    def from_settings(cls, settings: Settings) -> "Services":
        missing = settings.required_runtime_settings()
        if missing:
            missing_names = ", ".join(missing)
            raise RuntimeError(f"Missing required runtime settings: {missing_names}")
        weak = settings.weak_runtime_settings()
        if weak and settings.app_env not in {"development", "test"}:
            weak_names = ", ".join(weak)
            raise RuntimeError(
                f"Sample or too short secrets are rejected in {settings.app_env}: {weak_names}"
            )
        return cls(
            database=Database(settings.database_url),
            redis=RedisClient(settings.redis_url),
            passwords=PasswordHasher(settings.password_hasher),
            tokens=TokenService(
                secret=settings.jwt_secret,
                access_ttl_seconds=settings.jwt_access_ttl_seconds,
                refresh_ttl_days=settings.jwt_refresh_ttl_days,
            ),
            nutrition=NutritionEngine.from_settings(settings),
        )

    async def start(self) -> None:
        logger.info("infrastructure_initialized")

    async def check_health(
        self, *, timeout: float = HEALTHCHECK_TIMEOUT_SECONDS
    ) -> None:
        try:
            checks = await asyncio.wait_for(
                asyncio.gather(
                    self.database.ping(),
                    self.redis.ping(),
                    return_exceptions=True,
                ),
                timeout=timeout,
            )
        except TimeoutError:
            checks = [TimeoutError()]
        if any(isinstance(result, Exception) for result in checks):
            logger.warning(
                "dependency_healthcheck_failed",
                extra={"error_code": "dependency_unavailable"},
            )
            raise DependencyUnavailable()

    async def close(self) -> None:
        await asyncio.gather(
            self.database.close(),
            self.redis.close(),
            return_exceptions=True,
        )
