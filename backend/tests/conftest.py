from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.models  # noqa: F401  (registers tables on Base.metadata)
from app.auth.passwords import PasswordHasher
from app.auth.tokens import TokenService
from app.core.config import Settings
from app.core.db import Base, Database
from app.core.redis import RedisClient
from app.core.services import Services
from app.main import create_app

API_PREFIX = "/api/v1"
TEST_JWT_SECRET = "unit-test-signing-key-with-enough-entropy"
TEST_PASSWORD = "correct horse battery staple"


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        app_env="test",
        api_prefix=API_PREFIX,
        database_url=f"sqlite+aiosqlite:///{tmp_path}/foodai-test.db",
        redis_url="redis://localhost:6379/0",
        jwt_secret=TEST_JWT_SECRET,
    )


@pytest_asyncio.fixture
async def services(test_settings: Settings) -> AsyncIterator[Services]:
    database = Database(test_settings.database_url)
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    container = Services(
        database=database,
        redis=RedisClient(test_settings.redis_url),
        passwords=PasswordHasher(test_settings.password_hasher),
        tokens=TokenService(
            secret=test_settings.jwt_secret,
            access_ttl_seconds=test_settings.jwt_access_ttl_seconds,
            refresh_ttl_days=test_settings.jwt_refresh_ttl_days,
        ),
    )
    try:
        yield container
    finally:
        await database.close()


@pytest.fixture
def app(test_settings: Settings, services: Services) -> FastAPI:
    application = create_app(test_settings)
    application.state.services = services
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def session(services: Services) -> AsyncIterator[AsyncSession]:
    async with services.database.sessions() as database_session:
        yield database_session


@pytest_asyncio.fixture
async def registered(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": "Anna@Example.com",
            "password": TEST_PASSWORD,
            "locale": "ru-RU",
            "accepted_terms_at": "2026-09-18T17:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
