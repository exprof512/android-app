"""Safe API error envelopes and exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class DependencyUnavailable(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="dependency_unavailable",
            message="A required service is temporarily unavailable.",
        )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": _request_id(request),
    }
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "reason": error["type"],
        }
        for error in exc.errors()
    ]
    return _response(
        request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details=details,
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "http_error"
    message = "Resource not found." if exc.status_code == 404 else "Request failed."
    return _response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={
            "request_id": _request_id(request),
            "endpoint": request.url.path,
            "method": request.method,
            "error_code": "internal_error",
        },
    )
    return _response(
        request,
        status_code=500,
        code="internal_error",
        message="An unexpected server error occurred.",
    )
