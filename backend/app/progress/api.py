"""Progress HTTP endpoints."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser
from app.progress.dependencies import get_progress_service
from app.progress.schemas import ProgressSummaryOut, WeightEntryCreate, WeightEntryOut
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


@router.get("/progress/summary", response_model=ProgressSummaryOut)
async def progress_summary(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    service: ProgressService = Depends(get_progress_service),
) -> ProgressSummaryOut:
    return await service.summary(user.id, on_date=date_)
