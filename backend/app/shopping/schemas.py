"""Shopping list API schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import DecimalOut

ShoppingCategory = Literal["vegetables", "meat", "dairy", "grains", "other"]


class ShoppingGenerateRequest(BaseModel):
    meal_plan_id: UUID
    from_date: date | None = None
    to_date: date | None = None
    exclude_available_products: bool = True


class ShoppingListItemOut(BaseModel):
    id: UUID
    display_name: str
    quantity_value: DecimalOut
    unit: str
    is_completed: bool
    source_recipe_count: int
    ingredient_id: UUID | None = None
    category: ShoppingCategory = "other"
    estimated_cost_amount: DecimalOut | None = None


class ShoppingListOut(BaseModel):
    id: UUID
    meal_plan_id: UUID
    from_date: date
    to_date: date
    status: str
    items: list[ShoppingListItemOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    estimated_total_amount: DecimalOut | None = None
    currency: str = "RUB"
    stale: bool = False
    plan_fingerprint: str | None = None
