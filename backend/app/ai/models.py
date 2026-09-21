"""AI text usage audit table."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import CHAR, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin


class AiTextUsage(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One row per text AI attempt or cache reuse; never stores prompts or secrets."""

    __tablename__ = "ai_text_usage"
    __table_args__ = (
        Index("ix_ai_text_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_text_usage_operation_model_created", "operation", "model", "created_at"),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    conversation_id: Mapped[UUID | None] = mapped_column(Uuid)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))
    request_fingerprint: Mapped[str | None] = mapped_column(CHAR(64))
    schema_version: Mapped[int | None] = mapped_column(SmallInteger)
