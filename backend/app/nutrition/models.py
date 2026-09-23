"""Nutrition diary log table."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin


class NutritionLog(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_logs"
    __table_args__ = (
        Index("ix_nutrition_logs_user_logged_on", "user_id", "logged_on"),
        Index(
            "uq_nutrition_logs_meal_plan_item",
            "meal_plan_item_id",
            unique=True,
            postgresql_where=text("meal_plan_item_id IS NOT NULL"),
            sqlite_where=text("meal_plan_item_id IS NOT NULL"),
        ),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_nutrition_logs_meal_type",
        ),
        CheckConstraint(
            "source IN ('meal_plan_item', 'recipe', 'manual')",
            name="ck_nutrition_logs_source",
        ),
        CheckConstraint("calories_kcal >= 0", name="ck_nutrition_logs_calories"),
        CheckConstraint(
            "protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_nutrition_logs_macros",
        ),
        CheckConstraint("servings > 0", name="ck_nutrition_logs_servings"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    logged_on: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    recipe_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="SET NULL")
    )
    meal_plan_item_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("meal_plan_items.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    calories_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    servings: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("1"))
    source: Mapped[str] = mapped_column(String(24), nullable=False)
