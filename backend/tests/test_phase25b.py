"""Phase 25B: one plan per day, shared consumption, photo quota, timezone."""

from __future__ import annotations

from datetime import UTC, date, datetime
from io import BytesIO

import pytest
from httpx import AsyncClient

from app.core.user_time import user_local_date
from app.integrations.openai.vision import (
    MockOpenAIVisionProvider,
    VisionFoodAnalysisResult,
    VisionFoodItem,
)
from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import auth


def test_user_local_date_crosses_midnight_in_profile_timezone():
    instant = datetime(2026, 1, 1, 22, 30, tzinfo=UTC)
    assert user_local_date("Europe/Moscow", instant) == date(2026, 1, 2)
    assert user_local_date("UTC", instant) == date(2026, 1, 1)


@pytest.mark.asyncio
async def test_second_generate_does_not_leave_two_ready_plans(
    client: AsyncClient, ready_user, session
):
    from tests.test_phase22_plan_continuity import _seed_fallback_ingredients

    await _seed_fallback_ingredients(session)
    tokens, _ = ready_user
    headers = auth(tokens)
    first = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 7, "force": False},
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 7, "force": True},
    )
    assert second.status_code == 201, second.text
    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today.status_code == 200, today.text
    assert today.json()["id"] == second.json()["id"]
    assert today.json()["id"] != first.json()["id"]


@pytest.mark.asyncio
async def test_eat_matches_diary_and_progress(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    item = generated.json()["items"][0]
    await client.post(
        f"{API_PREFIX}/meal-plan-items/{item['id']}/complete",
        headers=headers,
        params={"completed": True},
    )
    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress = await client.get(
        f"{API_PREFIX}/progress/summary",
        headers=headers,
        params={"date": START.isoformat()},
    )
    consumed = today.json()["day_progress"]["consumed_kcal"]
    diary = sum(row["calories_kcal"] for row in logs.json())
    assert consumed == diary
    assert consumed == item["nutrition"]["calories_kcal"]
    body = progress.json()
    if body.get("today") and body["today"]["date"] == START.isoformat():
        assert body["today"]["consumed_calories_kcal"] == consumed


@pytest.mark.asyncio
async def test_photo_quota_blocks_before_provider(client: AsyncClient, ready_user, app):
    tokens, _ = ready_user
    headers = auth(tokens)
    mock = MockOpenAIVisionProvider(
        [
            VisionFoodAnalysisResult(
                items=[
                    VisionFoodItem(
                        name="куриная грудка",
                        estimated_grams=100,
                        confidence=0.9,
                        notes=None,
                    )
                ],
                overall_confidence=0.9,
                warnings=[],
                model="mock-vision",
                duration_ms=1,
            )
        ]
        * 12
    )
    app.state.vision_provider = mock
    image = b"\xff\xd8\xff\xe0" + b"0" * 200
    limit = app.state.settings.entitlement_free_food_photo_per_day
    last = None
    for _ in range(limit + 1):
        last = await client.post(
            f"{API_PREFIX}/nutrition/photo/analyze",
            headers=headers,
            files={"file": ("meal.jpg", BytesIO(image), "image/jpeg")},
        )
    assert last is not None
    assert last.status_code == 429, last.text
    assert len(mock.calls) == limit


@pytest.mark.asyncio
async def test_photo_confirm_rejects_allergy(client: AsyncClient, ready_user, session):
    from decimal import Decimal

    from app.recipes.models import Ingredient
    from app.recipes.normalization import canonical_key

    ingredient = Ingredient(
        canonical_name="Арахис",
        normalized_name=canonical_key("Арахис"),
        default_unit="g",
        calories_per_100g=Decimal("567"),
        protein_per_100g=Decimal("26"),
        fat_per_100g=Decimal("49"),
        carbohydrate_per_100g=Decimal("16"),
        reference_price_per_100g=Decimal("20"),
        currency="RUB",
        source="seed",
        is_active=True,
    )
    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)
    tokens, _ = ready_user
    headers = auth(tokens)
    confirm = await client.post(
        f"{API_PREFIX}/nutrition/photo/confirm",
        headers=headers,
        json={
            "logged_on": START.isoformat(),
            "meal_type": "snack",
            "items": [
                {
                    "ingredient_id": str(ingredient.id),
                    "description": ingredient.canonical_name,
                    "quantity_g": 20,
                    "meal_type": "snack",
                }
            ],
        },
    )
    assert confirm.status_code == 422, confirm.text
    assert confirm.json()["error"]["code"] == "allergy_or_restriction"
