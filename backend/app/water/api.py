"""Water intake HTTP endpoints."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.dependencies import get_db_session
from app.water.schemas import WaterEntryCreate, WaterEntryOut, WaterTodayOut
from app.water.service import WaterService

router = APIRouter(tags=["water"])


@router.get("/water/today", response_model=WaterTodayOut)
async def water_today(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db_session),
) -> WaterTodayOut:
    return await WaterService(session).today(user.id, on_date=date_)


@router.post(
    "/water",
    response_model=WaterEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_water(
    payload: WaterEntryCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> WaterEntryOut:
    return await WaterService(session).add(user.id, payload)


@router.delete("/water/last", status_code=status.HTTP_204_NO_CONTENT)
async def delete_last_water(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await WaterService(session).delete_last(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/water/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_water(
    entry_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await WaterService(session).delete(user.id, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
