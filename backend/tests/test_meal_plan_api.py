"""Phase 6 meal plan tests — MockTextProvider only."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mock import MockTextProvider
from app.meal_plans.models import MealPlan, MealPlanItem
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from tests.conftest import API_PREFIX, TEST_PASSWORD
from tests.test_profile_api import PROFILE_PAYLOAD, auth, register

START = date(2026, 9, 21)


def _recipe(name: str, ingredients: list[dict], cook: int = 25) -> dict:
    return {
        "name": name,
        "description": None,
        "servings": 1,
        "cooking_method": "mixed",
        "cook_time_minutes": cook,
        "ingredients": ingredients,
        "steps": ["Подготовьте продукты.", "Приготовьте блюдо.", "Подайте."],
        "rationale": None,
    }


# Roughly 450 kcal each using catalog seeds; 4 meals ≈ 1800 kcal.
MEAL_INGREDIENTS = [
    {"name": "Куриная грудка", "quantity": 150, "unit": "g"},  # ~248
    {"name": "Рис", "quantity": 50, "unit": "g"},  # ~172
    {"name": "Брокколи", "quantity": 80, "unit": "g"},  # ~27
]  # ≈ 447 kcal


def valid_day_plan_payload() -> dict:
    recipes = [
        _recipe("Завтрак боул", MEAL_INGREDIENTS),
        _recipe("Обед курица", MEAL_INGREDIENTS),
        _recipe("Ужин курица", MEAL_INGREDIENTS),
        _recipe("Перекус творог", [
            {"name": "Творог", "quantity": 150, "unit": "g"},
            {"name": "Яблоко", "quantity": 1, "unit": "piece"},
        ], cook=10),
    ]
    slots = [
        {
            "planned_date": START.isoformat(),
            "meal_type": meal,
            "recipe_index": idx,
            "servings": 1,
        }
        for idx, meal in enumerate(("breakfast", "lunch", "dinner", "snack"))
    ]
    return {"recipes": recipes, "slots": slots, "rationale": "Тестовый день"}


async def _seed_catalog(session: AsyncSession) -> None:
    rows = (
        ("Куриная грудка", "g", 165, 31, 3.6, 0, 45, None, None),
        ("Рис", "g", 344, 7, 1, 78, 10, None, None),
        ("Брокколи", "g", 34, 2.8, 0.4, 7, 25, None, None),
        ("Творог", "g", 121, 17, 5, 3, 30, None, None),
        ("Яблоко", "g", 52, 0.3, 0.2, 14, 12, Decimal("180"), None),
        ("Гречка", "g", 343, 13, 3.4, 62, 12, None, None),
        ("Овсяные хлопья", "g", 366, 12, 7, 62, 11, None, None),
        ("Яйцо", "piece", 157, 13, 11, 1.1, 12, Decimal("55"), None),
    )
    for name, unit, kcal, p, f, c, price, piece, dens in rows:
        existing = (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.normalized_name == canonical_key(name)
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        session.add(
            Ingredient(
                canonical_name=name,
                normalized_name=canonical_key(name),
                default_unit=unit,
                calories_per_100g=Decimal(str(kcal)),
                protein_per_100g=Decimal(str(p)),
                fat_per_100g=Decimal(str(f)),
                carbohydrate_per_100g=Decimal(str(c)),
                reference_price_per_100g=Decimal(str(price)),
                currency="RUB",
                grams_per_piece=piece,
                density_g_per_ml=dens,
                source="seed",
                is_active=True,
            )
        )
    await session.commit()


@pytest.fixture
async def ready_user(client: AsyncClient, session: AsyncSession, app):
    await _seed_catalog(session)
    tokens = await register(client, "planner@example.com")
    response = await client.put(
        f"{API_PREFIX}/profile",
        headers=auth(tokens),
        json=PROFILE_PAYLOAD,
    )
    assert response.status_code == 200, response.text
    provider = MockTextProvider([valid_day_plan_payload()])
    app.state.text_ai_provider = provider
    return tokens, provider


@pytest.mark.asyncio
async def test_generate_today_and_idempotent_reuse(
    client: AsyncClient, ready_user, session: AsyncSession
):
    tokens, provider = ready_user

    first = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["status"] == "ready"
    assert len(body["items"]) == 4
    assert body["reused"] is False
    assert body["daily_targets"]["calories_kcal"] > 1000

    second = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] == body["id"]
    assert second.json()["reused"] is True
    # Second call must not hit the provider again.
    assert len(provider.calls) == 1

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    assert today.status_code == 200
    assert len(today.json()["items"]) == 4

    plans = (await session.execute(select(MealPlan))).scalars().all()
    assert len(plans) == 1


@pytest.mark.asyncio
async def test_complete_and_replace_item(client: AsyncClient, ready_user, app):
    tokens, provider = ready_user
    created = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["items"][0]["id"]

    done = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=auth(tokens),
    )
    assert done.status_code == 200, done.text
    assert done.json()["is_completed"] is True

    provider.enqueue(
        {
            "recipes": [_recipe("Новый завтрак", MEAL_INGREDIENTS)],
            "reason": "Больше овощей",
        }
    )
    replaced = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/replace",
        headers=auth(tokens),
    )
    assert replaced.status_code == 200, replaced.text
    names = {item["recipe"]["name"] for item in replaced.json()["items"]}
    assert "Новый завтрак" in names


@pytest.mark.asyncio
async def test_generate_requires_profile(client: AsyncClient, app):
    tokens = await register(client, "noprofile@example.com")
    app.state.text_ai_provider = MockTextProvider([valid_day_plan_payload()])
    response = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "profile_incomplete"


@pytest.mark.asyncio
async def test_recipe_readable_via_meal_plan(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    created = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    recipe_id = created.json()["items"][0]["recipe"]["id"]
    card = await client.get(
        f"{API_PREFIX}/recipes/{recipe_id}",
        headers=auth(tokens),
    )
    assert card.status_code == 200, card.text
    assert card.json()["id"] == recipe_id
