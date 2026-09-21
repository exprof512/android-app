"""Docker healthcheck for the idle Arq worker."""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from app.core.config import get_settings


async def check() -> None:
    client = Redis.from_url(get_settings().redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(check())
