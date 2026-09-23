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
from app.storage.provider import StorageProvider
from app.storage.s3 import S3StorageProvider

logger = logging.getLogger(__name__)

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
        storage: StorageProvider | None = None,
        settings: Settings | None = None,
        email_provider=None,
        rate_limiter=None,
    ) -> None:
        self.database = database
        self.redis = redis
        self.passwords = passwords
        self.tokens = tokens
        self.nutrition = nutrition
        self.text_provider = text_provider
        self.storage = storage
        self.settings = settings
        self.email_provider = email_provider
        self.rate_limiter = rate_limiter

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
        settings.validate_production_legal()
        storage = None
        if settings.app_env != "test":
            access = settings.s3_access_key or settings.minio_root_user
            secret = settings.s3_secret_key or settings.minio_root_password
            if access and secret:
                storage = S3StorageProvider(
                    endpoint_url=settings.s3_endpoint,
                    access_key=access,
                    secret_key=secret,
                    bucket=settings.s3_bucket,
                    region=settings.s3_region,
                    public_base_url=settings.media_public_base_url,
                    use_ssl=settings.s3_use_ssl,
                    presigned_ttl_seconds=settings.s3_presigned_url_ttl_seconds,
                )
        from app.core.rate_limit import MemoryRateLimiter, RedisRateLimiter
        from app.email.provider import MockEmailProvider

        email = MockEmailProvider()
        redis = RedisClient(settings.redis_url)
        limiter: object = (
            MemoryRateLimiter()
            if settings.app_env == "test"
            else RedisRateLimiter(redis)
        )
        return cls(
            database=Database(settings.database_url),
            redis=redis,
            passwords=PasswordHasher(settings.password_hasher),
            tokens=TokenService(
                secret=settings.jwt_secret,
                access_ttl_seconds=settings.jwt_access_ttl_seconds,
                refresh_ttl_days=settings.jwt_refresh_ttl_days,
            ),
            nutrition=NutritionEngine.from_settings(settings),
            storage=storage,
            settings=settings,
            email_provider=email,
            rate_limiter=limiter,
        )

    async def start(self) -> None:
        if isinstance(self.storage, S3StorageProvider):
            try:
                await self.storage.ensure_bucket()
            except Exception:
                logger.warning(
                    "storage_bucket_ensure_failed",
                    extra={"error_code": "storage_init"},
                )
        logger.info("infrastructure_initialized")

    async def check_health(
        self, *, timeout: float = HEALTHCHECK_TIMEOUT_SECONDS
    ) -> None:
        details = await self.check_health_details(timeout=timeout)
        required = ("postgres", "redis")
        if any(details[name] != "ok" for name in required):
            logger.warning(
                "dependency_healthcheck_failed",
                extra={"error_code": "dependency_unavailable"},
            )
            raise DependencyUnavailable()

    async def check_health_details(
        self, *, timeout: float = HEALTHCHECK_TIMEOUT_SECONDS
    ) -> dict[str, str]:
        """Return per-dependency status without secrets or connection strings."""

        async def _status(coro: object, label: str) -> tuple[str, str]:
            try:
                await coro  # type: ignore[misc]
                return label, "ok"
            except Exception:
                return label, "unavailable"

        async def _gather() -> dict[str, str]:
            jobs = [
                _status(self.database.ping(), "postgres"),
                _status(self.redis.ping(), "redis"),
            ]
            storage = self.storage
            if storage is not None and hasattr(storage, "ping"):
                jobs.append(_status(storage.ping(), "storage"))
            results = await asyncio.gather(*jobs)
            out = {name: status for name, status in results}
            if "storage" not in out:
                out["storage"] = "skipped"
            return out

        try:
            return await asyncio.wait_for(_gather(), timeout=timeout)
        except TimeoutError:
            return {
                "postgres": "unavailable",
                "redis": "unavailable",
                "storage": "unavailable",
            }

    async def close(self) -> None:
        await asyncio.gather(
            self.database.close(),
            self.redis.close(),
            return_exceptions=True,
        )
