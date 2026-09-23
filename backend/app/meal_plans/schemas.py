"""Meal plan API contracts."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import DecimalOut
from app.meal_plans import constants


class MealPlanGenerateRequest(BaseModel):
    start_date: date
    days: int = Field(default=7, ge=constants.DAYS_MIN, le=constants.DAYS_MAX)
    notes: str | None = Field(default=None, max_length=500)
    # When true, ignore idempotent hash reuse and archive any overlapping ready plan.
    force: bool = False


class MealPlanReplaceRequest(BaseModel):
    replace_reason: Literal[
        "dislike",
        "too_expensive",
        "too_long",
        "unavailable_ingredients",
        "nutrition_balance",
        "user_requested",
        "more_protein",
        "less_calories",
        "other",
    ] = "user_requested"


class MealPlanRegenerateRequest(BaseModel):
    scope: Literal["all", "day"] = "all"
    on_date: date | None = Field(default=None, alias="date")
    notes: str | None = Field(default=None, max_length=500)

    model_config = {"populate_by_name": True}


class DailyTargetsOut(BaseModel):
    calories_kcal: int
    protein_g: DecimalOut
    fat_g: DecimalOut
    carbohydrate_g: DecimalOut


class MacroProgressOut(BaseModel):
    consumed_g: DecimalOut
    target_g: DecimalOut
    remaining_g: DecimalOut


class DayProgressOut(BaseModel):
    consumed_kcal: int
    target_kcal: int
    remaining_kcal: int
    protein: MacroProgressOut
    fat: MacroProgressOut
    carbs: MacroProgressOut
    completed_meals: int
    planned_meals: int
    skipped_meals: int
    next_meal_item_id: UUID | None = None
    next_meal_type: str | None = None
    suggestions: list[str] = Field(default_factory=list)
    daily_estimated_cost_amount: DecimalOut | None = None


class WeekDayOut(BaseModel):
    date: date
    status: Literal["planned", "missing", "generating"]
    calories_kcal: int = 0
    protein_g: DecimalOut = Field(default=0)
    completed_meals: int = 0
    planned_meals: int = 0
    estimated_cost_amount: DecimalOut | None = None


class WeekSummaryOut(BaseModel):
    days: list[WeekDayOut] = Field(default_factory=list)


class MealPlanRecipeSummary(BaseModel):
    id: UUID
    name: str
    calories_kcal: int
    cook_time_minutes: int
    image: dict[str, object] = Field(
        default_factory=lambda: {"status": "pending", "thumbnail_url": None}
    )


class MealPlanItemOut(BaseModel):
    id: UUID
    date: date
    meal_type: str
    servings: DecimalOut
    sort_order: int
    status: str
    is_completed: bool
    nutrition: DailyTargetsOut
    estimated_cost_amount: DecimalOut
    recipe: MealPlanRecipeSummary


class MealPlanOut(BaseModel):
    id: UUID
    start_date: date
    end_date: date
    status: str
    daily_targets: DailyTargetsOut
    items: list[MealPlanItemOut]
    warnings: list[str] = Field(default_factory=list)
    reused: bool = False
    day_progress: DayProgressOut | None = None
    week_summary: WeekSummaryOut | None = None
