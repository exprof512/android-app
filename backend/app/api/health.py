"""Infrastructure readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.core.dependencies import get_services
from app.core.services import Services

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


class DependencyStatus(BaseModel):
    postgres: str
    redis: str
    storage: str


class HealthDepsResponse(BaseModel):
    status: str
    dependencies: DependencyStatus = Field(...)


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health(
    services: Services = Depends(get_services),
) -> HealthResponse:
    """Return ready only when required dependencies are reachable."""
    await services.check_health()
    return HealthResponse(status="ok")


@router.get(
    "/health/deps",
    response_model=HealthDepsResponse,
    include_in_schema=False,
)
async def health_deps(
    response: Response,
    services: Services = Depends(get_services),
) -> HealthDepsResponse:
    """Per-dependency readiness without secrets — for ops/scripts."""
    statuses = await services.check_health_details()
    required_ok = statuses["postgres"] == "ok" and statuses["redis"] == "ok"
    overall = "ok" if required_ok else "dependency_unavailable"
    if not required_ok:
        response.status_code = 503
    return HealthDepsResponse(
        status=overall,
        dependencies=DependencyStatus(**statuses),
    )
