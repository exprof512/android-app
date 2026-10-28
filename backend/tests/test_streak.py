"""Progress streak: consecutive days with food activity."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from app.auth.models import User
from app.auth.passwords import PasswordHasher
from app.core.user_time import user_local_date
from app.nutrition.models import NutritionLog
from app.progress.repository import ProgressRepository
from app.progress.service import ProgressService


async def _user(session, email: str) -> User:
    user = User(
        email=email,
        password_hash=PasswordHasher().hash("correct horse battery staple"),
        locale="ru-RU",
    )
    session.add(user)
    await session.flush()
    return user


def _log(user: User, day) -> NutritionLog:
    return NutritionLog(
        user_id=user.id,
        logged_on=day,
        meal_type="snack",
        description="Йогурт",
        calories_kcal=150,
        protein_g=Decimal("10"),
        fat_g=Decimal("4"),
        carbohydrate_g=Decimal("15"),
        source="manual",
    )


def _service(session) -> ProgressService:
    return ProgressService(session=session, repository=ProgressRepository(session))


@pytest.mark.asyncio
async def test_streak_counts_consecutive_days(session) -> None:
    user = await _user(session, "streak-a@example.com")
    today = user_local_date(None)
    for offset in (0, 1, 2, 4):
        session.add(_log(user, today - timedelta(days=offset)))
    await session.flush()

    out = await _service(session).streak(user.id)

    assert out.current_days == 3
    assert out.best_days == 3
    assert out.last_active_date == today


@pytest.mark.asyncio
async def test_streak_keeps_best_run_after_gap(session) -> None:
    user = await _user(session, "streak-b@example.com")
    today = user_local_date(None)
    for offset in (0, 1, 4, 5, 6, 7):
        session.add(_log(user, today - timedelta(days=offset)))
    await session.flush()

    out = await _service(session).streak(user.id)

    assert out.current_days == 2
    assert out.best_days == 4


@pytest.mark.asyncio
async def test_streak_is_zero_without_activity(session) -> None:
    user = await _user(session, "streak-c@example.com")
    await session.flush()

    out = await _service(session).streak(user.id)

    assert out.current_days == 0
    assert out.best_days == 0
    assert out.last_active_date is None
