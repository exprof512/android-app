"""FastAPI application factory for the FoodAI backend."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1 import create_api_router
from app.core.config import Settings, get_settings
from app.core.errors import (
    ApiError,
    api_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging
from app.core.services import Services

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    candidate = request.headers.get("X-Request-ID")
    try:
        return str(UUID(candidate)) if candidate else str(uuid4())
    except ValueError:
        return str(uuid4())


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.services is None:
            app.state.services = Services.from_settings(active_settings)
        services = app.state.services
        await services.start()
        try:
            yield
        finally:
            await services.close()

    app = FastAPI(
        title="FoodAI API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.services = None

    @app.middleware("http")
    async def request_logging(request: Request, call_next: object) -> Response:
        request.state.request_id = _request_id(request)
        started_at = time.perf_counter()
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request.state.request_id,
                "user_id": getattr(request.state, "user_id", None),
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000),
            },
        )
        return response

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(health_router)
    app.include_router(create_api_router(active_settings.api_prefix))
    return app


app = create_app()
