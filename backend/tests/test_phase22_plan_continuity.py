"""Phase 22 continuity: ensure today plan + week diversity."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import fallback_plans as fp
from app.ai.fallback_plans import build_catalog_meal_plan_proposal
from app.ai.mock import MockTextProvider
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import auth


async def _seed_fallback_ingredients(session: AsyncSession) -> None:
    rows = (
        ("Куриная грудка", "g", 165, 31, 3.6, 0, 45, None),
        ("Индейка", "g", 189, 29, 7, 0, 60, None),
        ("Говядина", "g", 250, 26, 15, 0, 75, None),
        ("Лосось", "g", 208, 20, 13, 0, 120, None),
        ("Треска", "g", 82, 18, 0.7, 0, 55, None),
        ("Яйцо", "piece", 157, 13, 11, 1.1, 12, Decimal("55")),
        ("Молоко", "ml", 60, 3.2, 3.2, 4.8, 9, None),
        ("Кефир", "ml", 51, 3.4, 2, 4.1, 9, None),
        ("Творог", "g", 121, 17, 5, 3, 30, None),
        ("Греческий йогурт", "g", 59, 10, 0.4, 3.6, 35, None),
        ("Сыр твёрдый", "g", 364, 25, 30, 2, 90, None),
        ("Гречка", "g", 343, 13, 3.4, 62, 12, None),
        ("Рис", "g", 344, 7, 1, 78, 10, None),
        ("Овсяные хлопья", "g", 366, 12, 7, 62, 11, None),
        ("Макароны", "g", 344, 11, 1.3, 70, 12, None),
        ("Фасоль", "g", 333, 21, 1.2, 60, 15, None),
        ("Чечевица", "g", 352, 24, 1, 63, 18, None),
        ("Картофель", "g", 77, 2, 0.4, 17, 5, None),
        ("Морковь", "g", 41, 0.9, 0.2, 10, 6, None),
        ("Брокколи", "g", 34, 2.8, 0.4, 7, 25, None),
        ("Помидор", "g", 18, 0.9, 0.2, 3.9, 20, Decimal("120")),
        ("Огурец", "g", 15, 0.7, 0.1, 3.6, 18, Decimal("100")),
        ("Яблоко", "g", 52, 0.3, 0.2, 14, 12, Decimal("180")),
        ("Банан", "g", 89, 1.1, 0.3, 23, 11, Decimal("120")),
        ("Черника", "g", 57, 0.7, 0.3, 14, 90, None),
        ("Миндаль", "g", 579, 21, 50, 22, 150, None),
        ("Хлеб цельнозерновой", "g", 247, 9, 3.4, 46, 12, Decimal("35")),
    )
    for name, unit, kcal, p, f, c, price, piece in rows:
        existing = (
            await session.execute(
                select(Ingredient).where(Ingredient.normalized_name == canonical_key(name))
            )
        ).scalar_one_or_none()
        if existing is not None:
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
                reference_price_per_100g=Decimal(str(price)) if price is not None else None,
                currency="RUB" if price is not None else None,
                grams_per_piece=piece,
                density_g_per_ml=Decimal("1.03") if unit == "ml" else None,
                source="seed",
                is_active=True,
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_today_auto_generates_when_missing(
    client: AsyncClient, ready_user, session: AsyncSession, app
):
    await _seed_fallback_ingredients(session)
    tokens, _provider = ready_user
    headers = auth(tokens)
    # Force catalog path: empty AI responses.
    app.state.text_ai_provider = MockTextProvider([])

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today.status_code == 200, today.text
    body = today.json()
    assert body["items"]
    assert body["day_progress"] is not None
    assert body["day_progress"]["planned_meals"] >= 1

    today2 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today2.status_code == 200
    assert today2.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_catalog_fallback_rotates_meals_across_days(session: AsyncSession):
    await _seed_fallback_ingredients(session)
    proposal = await build_catalog_meal_plan_proposal(
        session,
        start_date=START,
        end_date=START + timedelta(days=6),
        meals_per_day=4,
    )
    breakfasts = [
        proposal.recipes[slot.recipe_index].name
        for slot in proposal.slots
        if slot.meal_type == "breakfast"
    ]
    assert len(breakfasts) == 7
    assert len(set(breakfasts)) >= 5, breakfasts
    lunches = [
        proposal.recipes[slot.recipe_index].name
        for slot in proposal.slots
        if slot.meal_type == "lunch"
    ]
    assert len(set(lunches)) >= 5, lunches


def test_fallback_template_pools_are_unique():
    assert len({n for n, _ in fp._BREAKFASTS}) == len(fp._BREAKFASTS)
    assert len({n for n, _ in fp._LUNCHES}) == len(fp._LUNCHES)
    assert len({n for n, _ in fp._DINNERS}) == len(fp._DINNERS)
