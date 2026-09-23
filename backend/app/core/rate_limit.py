"""Redis-backed rate limiting for auth and analytics endpoints."""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.errors import ApiError

logger = logging.getLogger(__name__)


class RateLimited(ApiError):
    def __init__(self, *, retry_after_seconds: int = 60) -> None:
        super().__init__(
            status_code=429,
            code="rate_limited",
            message="Слишком много запросов. Попробуйте позже.",
            headers={"Retry-After": str(retry_after_seconds)},
        )


class RateLimiter(Protocol):
    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None: ...


class MemoryRateLimiter:
    """Process-local counter for unit tests without Redis."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        del window_seconds  # fixed window not simulated in memory tests
        current = self._counts.get(key, 0) + 1
        self._counts[key] = current
        if current > limit:
            raise RateLimited()

    def clear(self) -> None:
        self._counts.clear()


class RedisRateLimiter:
    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        try:
            pipe = self._redis.client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = await pipe.execute()
            if int(count) > limit:
                raise RateLimited(retry_after_seconds=window_seconds)
        except RateLimited:
            raise
        except Exception:
            # Fail open for product flows if Redis is briefly unavailable.
            logger.warning("rate_limit_unavailable", extra={"error_code": "rate_limit"})
