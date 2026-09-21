"""Application infrastructure container."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import Settings
from app.core.db import Database
from app.core.errors import DependencyUnavailable
from app.core.redis import RedisClient

logger = logging.getLogger(__name__)


class Services:
    """Explicit dependency container shared by HTTP handlers."""

    def __init__(self, database: Database, redis: RedisClient) -> None:
        self.database = database
        self.redis = redis

    @classmethod
    def from_settings(cls, settings: Settings) -> "Services":
        missing = settings.required_runtime_settings()
        if missing:
            missing_names = ", ".join(missing)
            raise RuntimeError(f"Missing required runtime settings: {missing_names}")
        return cls(
            database=Database(settings.database_url),
            redis=RedisClient(settings.redis_url),
        )

    async def start(self) -> None:
        logger.info("infrastructure_initialized")

    async def check_health(self) -> None:
        checks = await asyncio.gather(
            self.database.ping(),
            self.redis.ping(),
            return_exceptions=True,
        )
        if any(isinstance(result, Exception) for result in checks):
            logger.warning("dependency_healthcheck_failed", extra={"error_code": "dependency_unavailable"})
            raise DependencyUnavailable()

    async def close(self) -> None:
        await asyncio.gather(
            self.database.close(),
            self.redis.close(),
            return_exceptions=True,
        )
