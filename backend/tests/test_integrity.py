"""Regression tests: parallel plan generation and quota windows stay consistent."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.auth.passwords import PasswordHasher
from app.entitlements import constants
from app.entitlements.errors import UsageLimitExceeded
from app.entitlements.repository import EntitlementsRepository
from app.entitlements.service import EntitlementsService
from app.meal_plans.repository import MealPlanRepository
from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import (  # noqa: F401  (pytest fixture)
    START,
    ready_user,
    valid_day_plan_payload,
)
from tests.test_profile_api import auth


@pytest.mark.asyncio
async def test_generation_conflict_reuses_existing_plan(
    client: AsyncClient, ready_user, monkeypatch
) -> None:
    tokens, provider = ready_user
    headers = auth(tokens)
    payload = {"start_date": START.isoformat(), "days": 1}

    first = await client.post(
        f"{API_PREFIX}/meal-plans/generate", headers=headers, json=payload
    )
    assert first.status_code == 201, first.text
    plan_id = first.json()["id"]
    provider.enqueue(valid_day_plan_payload())

    async def _conflict(*args, **kwargs):
        raise IntegrityError("INSERT INTO meal_plans", {}, Exception("duplicate key"))

    with monkeypatch.context() as patch:
        patch.setattr(MealPlanRepository, "add_plan", _conflict)
        second = await client.post(
            f"{API_PREFIX}/meal-plans/generate",
            headers=headers,
            json={**payload, "force": True},
        )

    assert second.status_code == 201, second.text
    assert second.json()["id"] == plan_id
    assert second.json()["reused"] is True


@pytest.mark.asyncio
async def test_usage_window_never_exceeds_limit(session, test_settings) -> None:
    settings = test_settings.model_copy(
        update={"entitlement_free_meal_plan_per_day": 1}
    )
    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash=PasswordHasher().hash("Password123!"),
        locale="ru-RU",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    service = EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=settings,
    )
    await service.ensure_free_subscription(user.id)

    status = await service.consume(
        user.id, constants.FEATURE_MEAL_PLAN_GENERATE
    )
    assert status.used_value == 1
    assert status.remaining == 0

    with pytest.raises(UsageLimitExceeded):
        await service.consume(user.id, constants.FEATURE_MEAL_PLAN_GENERATE)

    status = await service.usage_status(
        user.id, constants.FEATURE_MEAL_PLAN_GENERATE
    )
    assert status.used_value == 1
    assert status.limit_value == 1
