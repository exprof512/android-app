"""Profile and target-preview contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, PlainSerializer

from app.nutrition.engine import ActivityLevel, CalorieMode, GoalType, Sex
from app.profiles import limits

# Weights and money stay Decimal in Python and numeric in PostgreSQL; the JSON
# contract uses plain numbers.
DecimalOut = Annotated[
    Decimal, PlainSerializer(float, return_type=float, when_used="json")
]

AgeYears = Annotated[int, Field(ge=limits.AGE_YEARS_MIN, le=limits.AGE_YEARS_MAX)]
HeightCm = Annotated[
    Decimal, Field(ge=limits.HEIGHT_CM_MIN, le=limits.HEIGHT_CM_MAX, decimal_places=2)
]
WeightKg = Annotated[
    Decimal, Field(ge=limits.WEIGHT_KG_MIN, le=limits.WEIGHT_KG_MAX, decimal_places=2)
]
WeeklyChangeKg = Annotated[
    Decimal,
    Field(
        ge=limits.WEEKLY_CHANGE_KG_MIN,
        le=limits.WEEKLY_CHANGE_KG_MAX,
        decimal_places=2,
    ),
]
CalorieValue = Annotated[
    int, Field(ge=limits.CALORIE_VALUE_MIN, le=limits.CALORIE_VALUE_MAX)
]
MealsPerDay = Annotated[
    int, Field(ge=limits.MEALS_PER_DAY_MIN, le=limits.MEALS_PER_DAY_MAX)
]
HouseholdSize = Annotated[
    int, Field(ge=limits.HOUSEHOLD_SIZE_MIN, le=limits.HOUSEHOLD_SIZE_MAX)
]
CookTimeMinutes = Annotated[
    int, Field(ge=limits.COOK_TIME_MINUTES_MIN, le=limits.COOK_TIME_MINUTES_MAX)
]
Budget = Annotated[
    Decimal, Field(ge=limits.BUDGET_MIN, le=limits.BUDGET_MAX, decimal_places=2)
]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
FoodName = Annotated[str, Field(min_length=1, max_length=limits.FOOD_NAME_MAX_LENGTH)]
FoodList = Annotated[list[FoodName], Field(max_length=limits.FOOD_LIST_MAX_ITEMS)]
Quantity = Annotated[
    Decimal, Field(gt=limits.QUANTITY_MIN, le=limits.QUANTITY_MAX, decimal_places=2)
]


class PantryItem(BaseModel):
    name: FoodName
    quantity: Quantity
    unit: str = Field(pattern=r"^(" + "|".join(limits.UNITS) + r")$")
    expires_on: date | None = None


class PantryItemResponse(BaseModel):
    name: str
    quantity: DecimalOut
    unit: str
    expires_on: date | None


class TargetPreviewRequest(BaseModel):
    """Anthropometrics and goal; `POST /profile/calculate-target` stores nothing."""

    sex: Sex
    age_years: AgeYears
    height_cm: HeightCm
    current_weight_kg: WeightKg
    activity_level: ActivityLevel
    goal_type: GoalType
    target_weight_kg: WeightKg | None = None
    desired_weekly_change_kg: WeeklyChangeKg | None = None
    daily_calorie_mode: CalorieMode = "auto"
    daily_calorie_value: CalorieValue | None = None


class ProfileUpdateRequest(TargetPreviewRequest):
    """`PUT /profile` replaces the editable questionnaire in one transaction."""

    meals_per_day: MealsPerDay
    grocery_budget_weekly: Budget | None = None
    currency: Currency = limits.DEFAULT_CURRENCY
    max_cook_time_minutes: CookTimeMinutes | None = None
    household_size: HouseholdSize = 1
    timezone: str | None = Field(default=None, max_length=64)
    liked_foods: FoodList = []
    disliked_foods: FoodList = []
    excluded_foods: FoodList = []
    allergies: FoodList = []
    available_products: Annotated[
        list[PantryItem], Field(max_length=limits.PANTRY_MAX_ITEMS)
    ] = []


class MacroTargets(BaseModel):
    protein: int
    fat: int
    carbohydrate: int


class TargetPreviewResponse(BaseModel):
    bmr_kcal: int
    tdee_kcal: int
    recommended_calorie_target_kcal: int
    applied_safety_floor_kcal: int
    macro_targets_g: MacroTargets
    warnings: list[str]


class ProfileFields(BaseModel):
    sex: str | None
    age_years: int | None
    height_cm: DecimalOut | None
    current_weight_kg: DecimalOut | None
    activity_level: str | None
    meals_per_day: int | None
    daily_calorie_mode: str | None
    daily_calorie_value: int | None
    grocery_budget_weekly: DecimalOut | None
    currency: str | None
    max_cook_time_minutes: int | None
    household_size: int | None
    timezone: str | None


class GoalView(BaseModel):
    id: UUID
    goal_type: str
    status: str
    start_weight_kg: DecimalOut | None
    target_weight_kg: DecimalOut | None
    desired_weekly_change_kg: DecimalOut | None
    calorie_target_kcal: int
    macro_targets_g: MacroTargets
    bmr_kcal: int
    tdee_kcal: int
    safety_floor_kcal: int
    started_at: date | None


class Preferences(BaseModel):
    liked_foods: list[str]
    disliked_foods: list[str]


class Restrictions(BaseModel):
    excluded_foods: list[str]
    allergies: list[str]


class ProfileResponse(BaseModel):
    profile: ProfileFields
    goal: GoalView | None
    preferences: Preferences
    restrictions: Restrictions
    available_products: list[PantryItemResponse]
    warnings: list[str]
