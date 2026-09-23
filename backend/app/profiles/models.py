"""Profile, goal, preference, restriction and pantry tables."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin
from app.nutrition.engine import ACTIVITY_LEVELS, CALORIE_MODES, GOAL_TYPES, SEXES
from app.profiles import limits


class UserProfile(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One questionnaire row per user; every field is optional until onboarding."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        CheckConstraint(
            f"sex IS NULL OR sex IN ({limits.sql_in_list(SEXES)})",
            name="ck_user_profiles_sex",
        ),
        CheckConstraint(
            f"activity_level IS NULL OR activity_level IN ({limits.sql_in_list(ACTIVITY_LEVELS)})",
            name="ck_user_profiles_activity_level",
        ),
        CheckConstraint(
            f"daily_calorie_mode IS NULL OR daily_calorie_mode IN ({limits.sql_in_list(CALORIE_MODES)})",
            name="ck_user_profiles_daily_calorie_mode",
        ),
        CheckConstraint(
            f"age_years IS NULL OR age_years BETWEEN {limits.AGE_YEARS_MIN} AND {limits.AGE_YEARS_MAX}",
            name="ck_user_profiles_age_years",
        ),
        CheckConstraint(
            f"height_cm IS NULL OR height_cm BETWEEN {limits.HEIGHT_CM_MIN} AND {limits.HEIGHT_CM_MAX}",
            name="ck_user_profiles_height_cm",
        ),
        CheckConstraint(
            f"current_weight_kg IS NULL OR current_weight_kg BETWEEN {limits.WEIGHT_KG_MIN} AND {limits.WEIGHT_KG_MAX}",
            name="ck_user_profiles_current_weight_kg",
        ),
        CheckConstraint(
            f"meals_per_day IS NULL OR meals_per_day BETWEEN {limits.MEALS_PER_DAY_MIN} AND {limits.MEALS_PER_DAY_MAX}",
            name="ck_user_profiles_meals_per_day",
        ),
        CheckConstraint(
            f"daily_calorie_value IS NULL OR daily_calorie_value BETWEEN {limits.CALORIE_VALUE_MIN} AND {limits.CALORIE_VALUE_MAX}",
            name="ck_user_profiles_daily_calorie_value",
        ),
        CheckConstraint(
            f"grocery_budget_weekly IS NULL OR grocery_budget_weekly >= {limits.BUDGET_MIN}",
            name="ck_user_profiles_grocery_budget_weekly",
        ),
        CheckConstraint(
            f"max_cook_time_minutes IS NULL OR max_cook_time_minutes BETWEEN {limits.COOK_TIME_MINUTES_MIN} AND {limits.COOK_TIME_MINUTES_MAX}",
            name="ck_user_profiles_max_cook_time_minutes",
        ),
        CheckConstraint(
            f"household_size IS NULL OR household_size BETWEEN {limits.HOUSEHOLD_SIZE_MIN} AND {limits.HOUSEHOLD_SIZE_MAX}",
            name="ck_user_profiles_household_size",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    sex: Mapped[str | None] = mapped_column(String(16))
    age_years: Mapped[int | None] = mapped_column(SmallInteger)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    current_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    activity_level: Mapped[str | None] = mapped_column(String(32))
    meals_per_day: Mapped[int | None] = mapped_column(SmallInteger)
    daily_calorie_mode: Mapped[str | None] = mapped_column(String(16))
    daily_calorie_value: Mapped[int | None] = mapped_column(Integer)
    grocery_budget_weekly: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    max_cook_time_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    household_size: Mapped[int | None] = mapped_column(SmallInteger)
    timezone: Mapped[str | None] = mapped_column(String(64))
    active_goal_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("goals.id", ondelete="SET NULL")
    )


class Goal(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A target snapshot; recalculating the profile updates the active goal."""

    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_user_id_status_started_at", "user_id", "status", text("started_at DESC")),
        Index(
            "uq_goals_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        CheckConstraint(
            f"goal_type IN ({limits.sql_in_list(GOAL_TYPES)})", name="ck_goals_goal_type"
        ),
        CheckConstraint(
            f"status IN ({limits.sql_in_list(limits.GOAL_STATUSES)})", name="ck_goals_status"
        ),
        CheckConstraint(
            f"desired_weekly_change_kg IS NULL OR desired_weekly_change_kg BETWEEN {limits.WEEKLY_CHANGE_KG_MIN} AND {limits.WEEKLY_CHANGE_KG_MAX}",
            name="ck_goals_desired_weekly_change_kg",
        ),
        CheckConstraint("calorie_target_kcal > 0", name="ck_goals_calorie_target_kcal"),
        CheckConstraint("safety_floor_kcal > 0", name="ck_goals_safety_floor_kcal"),
        CheckConstraint(
            "protein_target_g >= 0 AND fat_target_g >= 0 AND carbohydrate_target_g >= 0",
            name="ck_goals_macro_targets",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    desired_weekly_change_kg: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    calorie_target_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_target_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    bmr_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    tdee_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_floor_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    started_at: Mapped[date | None] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    nutrition_policy_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="v1"
    )


class FoodPreference(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_food_name",
            "preference_type",
            name="uq_food_preferences_user_name_type",
        ),
        CheckConstraint(
            f"preference_type IN ({limits.sql_in_list(limits.PREFERENCE_TYPES)})",
            name="ck_food_preferences_preference_type",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    normalized_food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preference_type: Mapped[str] = mapped_column(String(16), nullable=False)


class FoodRestriction(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Allergies and exclusions only; the product stores no diagnosis."""

    __tablename__ = "food_restrictions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "normalized_food_name",
            "restriction_type",
            name="uq_food_restrictions_user_name_type",
        ),
        CheckConstraint(
            f"restriction_type IN ({limits.sql_in_list(limits.RESTRICTION_TYPES)})",
            name="ck_food_restrictions_restriction_type",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    normalized_food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    restriction_type: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16))


class AvailableProduct(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Pantry items; ingredient_id gains its foreign key with Phase 4 ingredients."""

    __tablename__ = "available_products"
    __table_args__ = (
        Index("ix_available_products_user_id_normalized_name", "user_id", "normalized_name"),
        CheckConstraint(
            f"unit IN ({limits.sql_in_list(limits.UNITS)})",
            name="ck_available_products_unit",
        ),
        CheckConstraint("quantity_value > 0", name="ck_available_products_quantity_value"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[UUID | None] = mapped_column(Uuid)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date)
