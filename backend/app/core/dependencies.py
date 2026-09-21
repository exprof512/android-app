"""FastAPI dependency injection for infrastructure services."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services import Services


def get_services(request: Request) -> Services:
    services = request.app.state.services
    if services is None:
        raise RuntimeError("Application services are not initialized.")
    return services


async def get_db_session(
    services: Services = Depends(get_services),
) -> AsyncIterator[AsyncSession]:
    async for session in services.database.session():
        yield session


def get_redis(
    services: Services = Depends(get_services),
) -> Redis:
    return services.redis.client
