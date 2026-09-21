"""Infrastructure readiness endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_services
from app.core.services import Services

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health(
    services: Services = Depends(get_services),
) -> HealthResponse:
    """Return ready only when PostgreSQL and Redis are reachable."""
    await services.check_health()
    return HealthResponse(status="ok")
