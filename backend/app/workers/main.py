"""Arq worker process with recipe image generation jobs."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.db import Database
from app.core.logging import configure_logging
from app.images.generator import generate_recipe_image
from app.storage.s3 import S3StorageProvider

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def arq_redis_settings(redis_url: str) -> RedisSettings:
    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        raise ValueError("REDIS_URL must be a redis URL.")
    database = int(parsed.path.strip("/") or "0")
    return RedisSettings(
        host=parsed.hostname,
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
    )


async def startup(ctx: dict[str, object]) -> None:
    database = Database(settings.database_url)
    storage = S3StorageProvider(
        endpoint_url=settings.s3_endpoint,
        access_key=settings.s3_access_key or settings.minio_root_user,
        secret_key=settings.s3_secret_key or settings.minio_root_password,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        public_base_url=settings.media_public_base_url,
        use_ssl=settings.s3_use_ssl,
        presigned_ttl_seconds=settings.s3_presigned_url_ttl_seconds,
    )
    try:
        await storage.ensure_bucket()
    except Exception:
        logger.warning("minio_bucket_ensure_failed", extra={"error_code": "storage_init"})
    ctx["database"] = database
    ctx["storage"] = storage
    ctx["settings"] = settings
    logger.info("worker_started")


async def shutdown(ctx: dict[str, object]) -> None:
    database = ctx.get("database")
    if isinstance(database, Database):
        await database.close()
    logger.info("worker_stopped")


class WorkerSettings:
    """Arq command target: ``arq app.workers.main.WorkerSettings``."""

    functions = [generate_recipe_image]
    redis_settings = arq_redis_settings(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    health_check_interval = 10
    max_jobs = 2
