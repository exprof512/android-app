"""Minimal Arq worker process; product jobs are intentionally not registered yet."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging

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


async def idle(_: dict[str, object]) -> None:
    """A no-op reserved job that lets Arq boot and remain idle."""

    logger.info("worker_idle_job_received")


async def startup(_: dict[str, object]) -> None:
    logger.info("worker_started")


async def shutdown(_: dict[str, object]) -> None:
    logger.info("worker_stopped")


class WorkerSettings:
    """Arq command target: ``arq app.workers.main.WorkerSettings``."""

    functions = [idle]
    redis_settings = arq_redis_settings(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    health_check_interval = 10
    max_jobs = 1
