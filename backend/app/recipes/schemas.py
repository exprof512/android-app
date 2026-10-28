"""Dish card contract."""

from __future__ import annotations

from decimal import Decimal

from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import DecimalOut


class DishCardNutrition(BaseModel):
    calories_kcal: int
    protein_g: DecimalOut
    fat_g: DecimalOut
    carbohydrate_g: DecimalOut


class DishCardCost(BaseModel):
    amount: DecimalOut
    currency: str


class DishCardIngredient(BaseModel):
    name: str
    grams: DecimalOut
    quantity: DecimalOut
    unit: str
    cost: DecimalOut | None


class DishCardResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    cooking_method: str
    cook_time_minutes: int
    servings: int
    status: str
    nutrition_per_serving: DishCardNutrition
    estimated_cost_per_serving: DishCardCost
    ingredients: list[DishCardIngredient]
    steps: list[str]
    is_favorite: bool


class IngredientSubstitutionApplyRequest(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    replacement_name: str = Field(min_length=1, max_length=255)
    quantity_g: Decimal | None = Field(default=None, gt=0, le=5000)
