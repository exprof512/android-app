"""Water intake API schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


DEFAULT_WATER_GOAL_ML = 2000


class WaterEntryCreate(BaseModel):
    amount_ml: int = Field(gt=0, le=5000)
    recorded_on: date | None = None


class WaterEntryOut(BaseModel):
    id: UUID
    recorded_on: date
    amount_ml: int
    created_at: datetime


class WaterTodayOut(BaseModel):
    date: date
    total_ml: int
    goal_ml: int = DEFAULT_WATER_GOAL_ML
    entries: list[WaterEntryOut] = Field(default_factory=list)
