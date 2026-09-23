"""Product analytics event storage."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base
from app.core.models import UuidPrimaryKeyMixin, utcnow

JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class ProductEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "product_events"
    __table_args__ = (
        Index("ix_product_events_name_occurred", "event_name", "occurred_at"),
        Index("ix_product_events_user_occurred", "user_id", "occurred_at"),
    )

    # No updated_at — append-only analytics.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32))
    app_version: Mapped[str | None] = mapped_column(String(32))
    session_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    properties: Mapped[dict] = mapped_column(JsonColumn, nullable=False, default=dict)
