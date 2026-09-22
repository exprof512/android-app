"""Docker healthcheck for the idle Arq worker (Redis + Postgres)."""

from __future__ import annotations

import asyncio
import sys

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def check() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        await redis.ping()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except Exception:
        sys.exit(1)
