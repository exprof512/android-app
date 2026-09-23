"""Admin AI usage endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.ai_usage import AIUsageAnalyticsService
from app.auth.dependencies import AdminUser
from app.core.dependencies import get_db_session

router = APIRouter(prefix="/admin/ai", tags=["admin"])


@router.get("/summary")
async def ai_summary(
    _admin: AdminUser,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AIUsageAnalyticsService(session).summary(from_date=from_, to_date=to)


@router.get("/daily")
async def ai_daily(
    _admin: AdminUser,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await AIUsageAnalyticsService(session).daily(from_date=from_, to_date=to)


@router.get("/by-operation")
async def ai_by_operation(
    _admin: AdminUser,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await AIUsageAnalyticsService(session).by_operation(from_date=from_, to_date=to)
