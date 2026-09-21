"""Redis client lifecycle management."""

from __future__ import annotations

from redis.asyncio import Redis


class RedisClient:
    """A small wrapper to keep Redis wiring behind application dependencies."""

    def __init__(self, redis_url: str) -> None:
        self.client = Redis.from_url(redis_url, decode_responses=True)

    async def ping(self) -> None:
        await self.client.ping()

    async def close(self) -> None:
        await self.client.aclose()
