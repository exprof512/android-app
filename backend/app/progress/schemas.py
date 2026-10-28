"""Progress API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import DecimalOut
from app.profiles import limits

WeightKg = Annotated[
    Decimal, Field(ge=limits.WEIGHT_KG_MIN, le=limits.WEIGHT_KG_MAX, decimal_places=2)
]


class WeightEntryCreate(BaseModel):
    measured_at: datetime
    weight_kg: WeightKg
    note: str | None = Field(default=None, max_length=500)


class WeightEntryOut(BaseModel):
    id: UUID
    measured_at: datetime
    weight_kg: DecimalOut
    note: str | None = None


class DailyNutritionBalanceOut(BaseModel):
    date: date
    target_calories_kcal: int | None = None
    consumed_calories_kcal: int = 0
    planned_calories_kcal: int = 0
    protein_g: DecimalOut = Field(default=Decimal("0"))
    fat_g: DecimalOut = Field(default=Decimal("0"))
    carbohydrate_g: DecimalOut = Field(default=Decimal("0"))
    completed_meals: int = 0
    planned_meals: int = 0


class ProgressSeriesPointOut(BaseModel):
    date: date
    consumed_kcal: int
    protein_g: DecimalOut
    completed_meals: int
    weight_kg: DecimalOut | None = None


class ProgressSummaryOut(BaseModel):
    current_weight_kg: DecimalOut | None = None
    start_weight_kg: DecimalOut | None = None
    target_weight_kg: DecimalOut | None = None
    goal_type: str | None = None
    weight_delta_kg: DecimalOut | None = None
    progress_percent: float | None = None
    trend_7d_kg: DecimalOut | None = None
    calorie_target_kcal: int | None = None
    today: DailyNutritionBalanceOut | None = None
    recent_entries: list[WeightEntryOut] = Field(default_factory=list)
    series: list[ProgressSeriesPointOut] = Field(default_factory=list)
    period_days: int | None = None
    disclaimer: str = (
        "Расчёты приблизительны и не заменяют врача или диетолога. "
        "FoodAI не гарантирует результат по весу."
    )
    warnings: list[str] = Field(default_factory=list)


class StreakOut(BaseModel):
    current_days: int = 0
    best_days: int = 0
    last_active_date: date | None = None
