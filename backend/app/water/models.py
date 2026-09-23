"""Water intake ORM model."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import UuidPrimaryKeyMixin, utcnow


class WaterEntry(UuidPrimaryKeyMixin, Base):
    __tablename__ = "water_entries"
    __table_args__ = (
        Index("ix_water_entries_user_recorded_on", "user_id", "recorded_on"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
