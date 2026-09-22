"""Subscription and usage_limit ORM models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin


class Subscription(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("tier IN ('free', 'premium')", name="ck_subscriptions_tier"),
        CheckConstraint(
            "status IN ('active', 'canceled', 'expired', 'past_due')",
            name="ck_subscriptions_status",
        ),
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255))
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsageLimit(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_limits"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "feature", "window_start", name="uq_usage_limits_window"
        ),
        Index(
            "ix_usage_limits_user_feature_window_end",
            "user_id",
            "feature",
            "window_end",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    feature: Mapped[str] = mapped_column(String(64), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    used_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
