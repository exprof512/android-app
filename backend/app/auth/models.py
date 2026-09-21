"""Identity and session tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, Boolean, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import TimestampMixin, UuidPrimaryKeyMixin, as_utc, utcnow


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A registered account; ``password_hash`` never leaves the service layer."""

    __tablename__ = "users"
    __table_args__ = (Index("uq_users_email_lower", text("lower(email)"), unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="ru-RU")
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """A hashed refresh token; the issued token value itself is never stored."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("uq_refresh_tokens_token_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_user_id_expires_at", "user_id", "expires_at"),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    family_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, at: datetime | None = None) -> bool:
        return as_utc(self.expires_at) <= (at or utcnow())

    def is_usable(self, at: datetime | None = None) -> bool:
        return not self.is_revoked and not self.is_expired(at)
