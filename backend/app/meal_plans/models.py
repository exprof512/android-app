"""Meal plan ORM models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin
from app.meal_plans import constants

if TYPE_CHECKING:
    from app.recipes.models import Recipe


class MealPlan(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_plans"
    __table_args__ = (
        Index("ix_meal_plans_user_start_date", "user_id", text("start_date DESC")),
        Index("ix_meal_plans_user_status_start", "user_id", "status", "start_date"),
        Index(
            "uq_meal_plans_user_generation_request_hash",
            "user_id",
            "generation_request_hash",
            unique=True,
            postgresql_where=text("generation_request_hash IS NOT NULL"),
            sqlite_where=text("generation_request_hash IS NOT NULL"),
        ),
        CheckConstraint(
            f"status IN ({constants.sql_in_list(constants.MEAL_PLAN_STATUSES)})",
            name="ck_meal_plans_status",
        ),
        CheckConstraint("end_date >= start_date", name="ck_meal_plans_date_range"),
        CheckConstraint(
            "calorie_target_kcal > 0 AND protein_target_g >= 0 "
            "AND fat_target_g >= 0 AND carbohydrate_target_g >= 0",
            name="ck_meal_plans_targets_non_negative",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("goals.id", ondelete="RESTRICT"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    calorie_target_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    generation_request_hash: Mapped[str | None] = mapped_column(CHAR(64))

    items: Mapped[list["MealPlanItem"]] = relationship(
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        order_by="MealPlanItem.planned_date, MealPlanItem.sort_order",
        lazy="selectin",
    )


class MealPlanItem(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_plan_items"
    __table_args__ = (
        UniqueConstraint(
            "meal_plan_id",
            "planned_date",
            "meal_type",
            "sort_order",
            name="uq_meal_plan_items_slot",
        ),
        Index("ix_meal_plan_items_plan_date", "meal_plan_id", "planned_date"),
        Index("ix_meal_plan_items_recipe_id", "recipe_id"),
        CheckConstraint(
            f"meal_type IN ({constants.sql_in_list(constants.MEAL_TYPES)})",
            name="ck_meal_plan_items_meal_type",
        ),
        CheckConstraint(
            f"status IN ({constants.sql_in_list(constants.MEAL_ITEM_STATUSES)})",
            name="ck_meal_plan_items_status",
        ),
        CheckConstraint("servings > 0", name="ck_meal_plan_items_servings"),
        CheckConstraint(
            "calories_kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_meal_plan_items_nutrition_non_negative",
        ),
    )

    meal_plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False
    )
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    servings: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="planned")
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calories_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    estimated_cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    meal_plan: Mapped[MealPlan] = relationship(back_populates="items")
    recipe: Mapped["Recipe"] = relationship(lazy="selectin")
