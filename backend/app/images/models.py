"""Recipe image and AI image usage tables."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin

IMAGE_STATUSES = ("pending", "processing", "ready", "failed")


class RecipeImage(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipe_images"
    __table_args__ = (
        Index("ix_recipe_images_recipe_created", "recipe_id", text("created_at DESC")),
        Index("ix_recipe_images_status_updated", "generation_status", "updated_at"),
        Index(
            "uq_recipe_images_primary",
            "recipe_id",
            unique=True,
            postgresql_where=text("is_primary IS TRUE"),
            sqlite_where=text("is_primary IS TRUE"),
        ),
        CheckConstraint(
            "generation_status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_recipe_images_generation_status",
        ),
        CheckConstraint(
            "(generation_status <> 'ready') OR "
            "(storage_key IS NOT NULL AND thumbnail_storage_key IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="ck_recipe_images_ready_has_assets",
        ),
    )

    recipe_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(1024))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String(16))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    generation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    generation_error: Mapped[str | None] = mapped_column(String(512))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_image_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("recipe_images.id", ondelete="SET NULL")
    )
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class AiImageUsage(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_image_usage"
    __table_args__ = (
        Index("ix_ai_image_usage_user_created", "user_id", text("created_at DESC")),
        Index(
            "ix_ai_image_usage_model_status_created",
            "model",
            "status",
            text("created_at DESC"),
        ),
        Index("ix_ai_image_usage_recipe_created", "recipe_id", text("created_at DESC")),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed', 'reused')",
            name="ck_ai_image_usage_status",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    recipe_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    recipe_image_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("recipe_images.id", ondelete="SET NULL")
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[str | None] = mapped_column(String(32))
    quality: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
