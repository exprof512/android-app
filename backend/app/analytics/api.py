"""Analytics HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.auth.dependencies import get_rate_limiter
from app.auth.errors import InvalidToken
from app.auth.models import User
from app.auth.service import AuthService
from app.auth.dependencies import get_auth_service
from app.core.dependencies import get_db_session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(tags=["analytics"])
optional_bearer = HTTPBearer(auto_error=False)


class AnalyticsEventIn(BaseModel):
    event_name: str = Field(max_length=64)
    event_version: int = Field(default=1, ge=1, le=100)
    occurred_at: datetime | None = None
    platform: str | None = Field(default=None, max_length=32)
    app_version: str | None = Field(default=None, max_length=32)
    session_id: str | None = Field(default=None, max_length=64)
    properties: dict[str, Any] = Field(default_factory=dict)


class AnalyticsBatchIn(BaseModel):
    events: list[AnalyticsEventIn] = Field(min_length=1, max_length=20)


class AnalyticsAccepted(BaseModel):
    accepted: int


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return await auth_service.authenticate(credentials.credentials)
    except InvalidToken:
        return None


@router.post("/events", response_model=AnalyticsAccepted)
async def post_events(
    payload: AnalyticsBatchIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    rate_limiter=Depends(get_rate_limiter),
    user: User | None = Depends(_optional_user),
) -> AnalyticsAccepted:
    service = AnalyticsService(session, rate_limiter=rate_limiter)
    accepted = await service.ingest(
        user_id=user.id if user else None,
        events=[e.model_dump() for e in payload.events],
        request_id=getattr(request.state, "request_id", None),
        client_key=_client_key(request),
    )
    return AnalyticsAccepted(accepted=accepted)
