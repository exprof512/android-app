"""Ingredient catalog, recipes and favorites."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin, utcnow
from app.recipes import constants

# JSONB in PostgreSQL, plain JSON in the SQLite test database.
JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class Ingredient(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Canonical nutrition and price reference; the only source the engine trusts."""

    __tablename__ = "ingredients"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_ingredients_normalized_name"),
        CheckConstraint(
            f"default_unit IN ({constants.sql_in_list(constants.RECIPE_UNITS)})",
            name="ck_ingredients_default_unit",
        ),
        CheckConstraint(
            f"source IN ({constants.sql_in_list(constants.INGREDIENT_SOURCES)})",
            name="ck_ingredients_source",
        ),
        CheckConstraint(
            "calories_per_100g >= 0 AND protein_per_100g >= 0 "
            "AND fat_per_100g >= 0 AND carbohydrate_per_100g >= 0",
            name="ck_ingredients_nutrition_non_negative",
        ),
        CheckConstraint(
            "reference_price_per_100g IS NULL OR reference_price_per_100g >= 0",
            name="ck_ingredients_reference_price_non_negative",
        ),
        CheckConstraint(
            "grams_per_piece IS NULL OR grams_per_piece > 0",
            name="ck_ingredients_grams_per_piece",
        ),
        CheckConstraint(
            "density_g_per_ml IS NULL OR density_g_per_ml > 0",
            name="ck_ingredients_density",
        ),
        CheckConstraint(
            "reference_price_per_100g IS NULL OR currency IS NOT NULL",
            name="ck_ingredients_price_needs_currency",
        ),
    )

    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    calories_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    protein_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    reference_price_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    # Conversion data for the units AI may use; NULL means the unit is not convertible.
    grams_per_piece: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    density_g_per_ml: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="seed")
    source_version: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Recipe(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A canonical dish; nutrition and cost are always backend calculations.

    ``recipe_ingredients.quantity_g`` covers the whole recipe, while the nutrition
    and cost columns hold per-serving values.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("recipe_fingerprint", name="uq_recipes_recipe_fingerprint"),
        Index("ix_recipes_status_updated_at", "status", text("updated_at DESC")),
        CheckConstraint(
            f"cooking_method IN ({constants.sql_in_list(constants.COOKING_METHODS)})",
            name="ck_recipes_cooking_method",
        ),
        CheckConstraint(
            f"status IN ({constants.sql_in_list(constants.RECIPE_STATUSES)})",
            name="ck_recipes_status",
        ),
        CheckConstraint(
            f"cook_time_minutes BETWEEN {constants.COOK_TIME_MINUTES_MIN} "
            f"AND {constants.COOK_TIME_MINUTES_MAX}",
            name="ck_recipes_cook_time_minutes",
        ),
        CheckConstraint(
            f"servings BETWEEN {constants.SERVINGS_MIN} AND {constants.SERVINGS_MAX}",
            name="ck_recipes_servings",
        ),
        CheckConstraint(
            "calories_kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_recipes_nutrition_non_negative",
        ),
        CheckConstraint(
            "estimated_cost_amount >= 0", name="ck_recipes_estimated_cost_non_negative"
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    recipe_fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    cooking_method: Mapped[str] = mapped_column(String(64), nullable=False)
    cook_time_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    servings: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    calories_kcal: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbohydrate_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    estimated_cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    steps: Mapped[list[str]] = mapped_column(JsonColumn, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    ai_model: Mapped[str | None] = mapped_column(String(128))

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.sort_order",
        lazy="selectin",
    )


class RecipeIngredient(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One catalog ingredient inside a recipe; ``quantity_g`` is authoritative."""

    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "sort_order", name="uq_recipe_ingredients_sort_order"),
        Index("ix_recipe_ingredients_ingredient_id", "ingredient_id"),
        CheckConstraint(
            f"unit IN ({constants.sql_in_list(constants.RECIPE_UNITS)})",
            name="ck_recipe_ingredients_unit",
        ),
        CheckConstraint("quantity_g > 0", name="ck_recipe_ingredients_quantity_g"),
        CheckConstraint("quantity_value > 0", name="ck_recipe_ingredients_quantity_value"),
        CheckConstraint(
            "cost_amount IS NULL OR cost_amount >= 0",
            name="ck_recipe_ingredients_cost_amount",
        ),
    )

    recipe_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


class UserRecipeFavorite(Base):
    """Link table that also grants the user access to the dish card."""

    __tablename__ = "user_recipe_favorites"
    __table_args__ = (
        Index(
            "ix_user_recipe_favorites_user_id_created_at",
            "user_id",
            text("created_at DESC"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
