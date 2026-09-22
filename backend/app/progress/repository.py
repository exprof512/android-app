"""Weight entry persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.progress.models import WeightEntry


class ProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: WeightEntry) -> WeightEntry:
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_entries(
        self,
        user_id: UUID,
        *,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        limit: int = 90,
    ) -> list[WeightEntry]:
        statement = (
            select(WeightEntry)
            .where(WeightEntry.user_id == user_id)
            .order_by(WeightEntry.measured_at.desc())
            .limit(limit)
        )
        if from_at is not None:
            statement = statement.where(WeightEntry.measured_at >= from_at)
        if to_at is not None:
            statement = statement.where(WeightEntry.measured_at <= to_at)
        return list((await self._session.execute(statement)).scalars())

    async def latest(self, user_id: UUID) -> WeightEntry | None:
        statement = (
            select(WeightEntry)
            .where(WeightEntry.user_id == user_id)
            .order_by(WeightEntry.measured_at.desc())
            .limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none()
