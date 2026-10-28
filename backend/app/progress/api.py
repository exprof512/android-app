"""Progress HTTP endpoints."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser
from app.progress.dependencies import get_progress_service
from app.progress.schemas import (
    ProgressSummaryOut,
    StreakOut,
    WeightEntryCreate,
    WeightEntryOut,
)
from app.progress.service import ProgressService

router = APIRouter(tags=["progress"])


@router.post(
    "/weight-entries",
    response_model=WeightEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_weight_entry(
    payload: WeightEntryCreate,
    user: CurrentUser,
    service: ProgressService = Depends(get_progress_service),
) -> WeightEntryOut:
    return await service.create_weight_entry(user.id, payload)


@router.get("/weight-entries", response_model=list[WeightEntryOut])
async def list_weight_entries(
    user: CurrentUser,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    service: ProgressService = Depends(get_progress_service),
) -> list[WeightEntryOut]:
    return await service.list_weight_entries(user.id, from_at=from_, to_at=to)


@router.get("/progress/streak", response_model=StreakOut)
async def progress_streak(
    user: CurrentUser,
    service: ProgressService = Depends(get_progress_service),
) -> StreakOut:
    return await service.streak(user.id)


@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    period: int | None = Query(default=None, ge=7, le=90),
    service: ProgressService = Depends(get_progress_service),
) -> ProgressSummaryOut:
    if period is not None and period not in {7, 30, 90}:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="period must be 7, 30, or 90")
    return await service.summary(user.id, on_date=date_, period=period)
