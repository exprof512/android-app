"""Calendar dates in the user's profile timezone.

Server process timezone is not the user's day. Callers that mean "today"
for a person must use this helper instead of ``date.today()``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_TIMEZONE = "Europe/Moscow"


def user_local_date(timezone_name: str | None, now: datetime | None = None) -> date:
    name = (timezone_name or "").strip() or DEFAULT_TIMEZONE
    try:
        zone = ZoneInfo(name)
    except Exception:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(zone).date()


def local_day_window(
    timezone_name: str | None, now: datetime | None = None
) -> tuple[datetime, datetime]:
    """Half-open [local midnight, next local midnight) as aware datetimes."""
    name = (timezone_name or "").strip() or DEFAULT_TIMEZONE
    try:
        zone = ZoneInfo(name)
    except Exception:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    local = moment.astimezone(zone)
    start = datetime(local.year, local.month, local.day, tzinfo=zone)
    return start, start + timedelta(days=1)


async def timezone_for_user(session: AsyncSession, user_id: UUID) -> str | None:
    from app.profiles.models import UserProfile

    profile = (
        await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:
        return None
    return profile.timezone


async def local_today_for_user(session: AsyncSession, user_id: UUID) -> date:
    return user_local_date(await timezone_for_user(session, user_id))
