"""Regression tests for the first hardening batch (auth throttling, AI context, idempotency)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.ai.context import AIContextBuilder
from app.ai.models import AiRecommendationRecord
from app.auth.models import IdempotencyKey
from app.nutrition.models import NutritionLog
from app.profiles.models import UserProfile
from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import ready_user  # noqa: F401  (pytest fixture)
from tests.test_phase20_ai import _user
from tests.test_profile_api import auth

LOGIN_EMAIL_LIMIT = 10
REGISTER_IP_LIMIT = 10
START = date(2026, 9, 21)


@pytest.mark.asyncio
async def test_login_is_rate_limited(client: AsyncClient) -> None:
    body = {"email": "brute-force@example.com", "password": "wrong-password"}
    for _ in range(LOGIN_EMAIL_LIMIT):
        response = await client.post(f"{API_PREFIX}/auth/login", json=body)
        assert response.status_code == 401, response.text
    blocked = await client.post(f"{API_PREFIX}/auth/login", json=body)
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["error"]["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_login_throttle_ignores_spoofed_first_hop(client: AsyncClient) -> None:
    body = {"email": "spoof@example.com", "password": "wrong-password"}
    for hop in range(LOGIN_EMAIL_LIMIT):
        response = await client.post(
            f"{API_PREFIX}/auth/login",
            json=body,
            headers={"X-Forwarded-For": f"10.0.0.{hop}, 9.9.9.9"},
        )
        assert response.status_code == 401, response.text
    blocked = await client.post(
        f"{API_PREFIX}/auth/login",
        json=body,
        headers={"X-Forwarded-For": "10.0.0.250, 9.9.9.9"},
    )
    assert blocked.status_code == 429, blocked.text


@pytest.mark.asyncio
async def test_register_is_rate_limited(client: AsyncClient) -> None:
    for index in range(REGISTER_IP_LIMIT):
        response = await client.post(
            f"{API_PREFIX}/auth/register",
            json={
                "email": f"signup-{index}@example.com",
                "password": "correct horse battery staple",
            },
        )
        assert response.status_code == 201, response.text
    blocked = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": "signup-overflow@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert blocked.status_code == 429, blocked.text


@pytest.mark.asyncio
async def test_ai_context_carries_consumed_and_remaining(session) -> None:
    user = await _user(session, "context-hardening@example.com")
    session.add(
        UserProfile(
            user_id=user.id,
            meals_per_day=3,
            max_cook_time_minutes=30,
            grocery_budget_weekly=Decimal("3000"),
            currency="RUB",
        )
    )
    await session.flush()

    context = await AIContextBuilder(session).build(user.id)

    assert isinstance(context["consumed_today"], dict)
    assert isinstance(context["remaining_today"], dict)
    assert context["consumed_today"]["calories_kcal"] == 0
    assert context["remaining_today"]["calories_kcal"] == 0
    assert "protein_g" in context["consumed_today"]
    assert "protein_g" in context["remaining_today"]


@pytest.mark.asyncio
async def test_apply_persists_idempotency_key_across_requests(
    client: AsyncClient, ready_user, session, services
) -> None:
    tokens, _ = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text
    recipe_id = generated.json()["items"][0]["recipe"]["id"]

    record = AiRecommendationRecord(
        user_id=uuid.UUID(tokens["user"]["id"]),
        operation="food_suggestion",
        status="proposed",
        context_version="v2",
        prompt_version="2",
        model="mock-text-model",
        recipe_id=uuid.UUID(recipe_id),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    key = "e2e-apply-idempotency-1"
    body = {
        "action_type": "create_nutrition_log",
        "payload": {"recipe_id": recipe_id, "meal_type": "snack"},
    }
    first = await client.post(
        f"{API_PREFIX}/ai/recommendations/{record.id}/apply",
        headers={**headers, "Idempotency-Key": key},
        json=body,
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        f"{API_PREFIX}/ai/recommendations/{record.id}/apply",
        headers={**headers, "Idempotency-Key": key},
        json=body,
    )
    assert second.status_code == 200, second.text
    assert (
        second.json()["result"]["nutrition_log_id"]
        == first.json()["result"]["nutrition_log_id"]
    )

    # The key must survive the request: a retry after a crash is served from it.
    async with services.database.sessions() as probe:
        stored = (
            await probe.execute(select(IdempotencyKey).where(IdempotencyKey.key == key))
        ).scalar_one_or_none()
    assert stored is not None

    logs = (
        await session.execute(
            select(func.count())
            .select_from(NutritionLog)
            .where(NutritionLog.user_id == uuid.UUID(tokens["user"]["id"]))
        )
    ).scalar_one()
    assert logs == 1
