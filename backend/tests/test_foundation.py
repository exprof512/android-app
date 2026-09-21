from __future__ import annotations

import socket
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import DependencyUnavailable
from app.main import create_app


class HealthyServices:
    async def start(self) -> None:
        return None

    async def check_health(self) -> None:
        return None

    async def close(self) -> None:
        return None


class UnhealthyServices(HealthyServices):
    async def check_health(self) -> None:
        raise DependencyUnavailable()


def test_health_returns_ok_with_request_id() -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url="postgresql+asyncpg://foodai:test@localhost/foodai",
            redis_url="redis://localhost:6379/0",
        )
    )
    app.state.services = HealthyServices()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_health_reports_dependency_failure_safely() -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url="postgresql+asyncpg://foodai:test@localhost/foodai",
            redis_url="redis://localhost:6379/0",
        )
    )
    app.state.services = UnhealthyServices()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"
    assert "test@" not in response.text


def test_settings_load_from_environment_without_network(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://foodai:test@localhost/foodai")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("OPENAI_API_KEY", "not-used-in-tests")
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network call")),
    )

    settings = Settings()

    assert settings.required_runtime_settings() == ()
    assert settings.openai_api_key == "not-used-in-tests"


def test_env_example_loads_without_secret_values() -> None:
    example = Path(__file__).parents[2] / ".env.example"

    settings = Settings(_env_file=example)

    assert settings.required_runtime_settings() == ("DATABASE_URL",)
    assert settings.image_max_concurrent_jobs is None
