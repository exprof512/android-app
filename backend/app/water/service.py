"""Water intake service."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, OwnershipDenied
from app.water.models import WaterEntry
from app.water.schemas import (
    DEFAULT_WATER_GOAL_ML,
    WaterEntryCreate,
    WaterEntryOut,
    WaterTodayOut,
)


class WaterEntryNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="water_entry_not_found",
            message="Запись о воде не найдена.",
        )


class WaterService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def today(self, user_id: UUID, on_date: date | None = None) -> WaterTodayOut:
        from app.core.user_time import local_today_for_user

        day = on_date or await local_today_for_user(self._session, user_id)
        entries = list(
            (
                await self._session.execute(
                    select(WaterEntry)
                    .where(
                        WaterEntry.user_id == user_id,
                        WaterEntry.recorded_on == day,
                    )
                    .order_by(WaterEntry.created_at.asc())
                )
            ).scalars()
        )
        total = sum(e.amount_ml for e in entries)
        return WaterTodayOut(
            date=day,
            total_ml=total,
            goal_ml=DEFAULT_WATER_GOAL_ML,
            entries=[self._out(e) for e in entries],
        )

    async def add(self, user_id: UUID, payload: WaterEntryCreate) -> WaterEntryOut:
        from app.core.user_time import local_today_for_user

        day = payload.recorded_on or await local_today_for_user(self._session, user_id)
        entry = WaterEntry(
            user_id=user_id,
            recorded_on=day,
            amount_ml=payload.amount_ml,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return self._out(entry)

    async def delete_last(self, user_id: UUID) -> None:
        entry = (
            await self._session.execute(
                select(WaterEntry)
                .where(WaterEntry.user_id == user_id)
                .order_by(WaterEntry.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if entry is None:
            raise WaterEntryNotFound()
        await self._session.delete(entry)
        await self._session.commit()

    async def delete(self, user_id: UUID, entry_id: UUID) -> None:
        entry = await self._session.get(WaterEntry, entry_id)
        if entry is None:
            raise WaterEntryNotFound()
        if entry.user_id != user_id:
            raise OwnershipDenied()
        await self._session.delete(entry)
        await self._session.commit()

    @staticmethod
    def _out(entry: WaterEntry) -> WaterEntryOut:
        return WaterEntryOut(
            id=entry.id,
            recorded_on=entry.recorded_on,
            amount_ml=entry.amount_ml,
            created_at=entry.created_at,
        )
