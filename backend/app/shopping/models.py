"""Shopping list ORM models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin, utcnow


class ShoppingList(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shopping_lists"
    __table_args__ = (
        CheckConstraint("status IN ('ready', 'archived')", name="ck_shopping_lists_status"),
        CheckConstraint("to_date >= from_date", name="ck_shopping_lists_date_range"),
        Index("ix_shopping_lists_user_updated_at", "user_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    meal_plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimated_total_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")

    items: Mapped[list[ShoppingListItem]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingListItem.display_name",
    )


class ShoppingListItem(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shopping_list_items"
    __table_args__ = (
        UniqueConstraint(
            "shopping_list_id",
            "normalized_name",
            "unit",
            name="uq_shopping_list_items_name_unit",
        ),
        CheckConstraint("quantity_value > 0", name="ck_shopping_list_items_quantity"),
        CheckConstraint(
            "unit IN ('g', 'kg', 'ml', 'l', 'piece', 'pack', 'tbsp', 'tsp')",
            name="ck_shopping_list_items_unit",
        ),
        Index("ix_shopping_list_items_list_id", "shopping_list_id"),
    )

    shopping_list_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
    )
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_recipe_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
