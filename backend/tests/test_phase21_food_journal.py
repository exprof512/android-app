"""Phase 21 food journal + photo vision (mocks only)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.integrations.openai.vision import (
    MockOpenAIVisionProvider,
    VisionFoodAnalysisResult,
    VisionFoodItem,
)
from app.nutrition.food_match import match_food_name, nutrition_for_grams
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from app.recipes.repository import RecipeRepository

API = "/api/v1"


async def _register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "locale": "ru-RU",
            "accepted_terms_at": "2026-09-18T17:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(session, *names: str) -> None:
    specs = {
        "Куриная грудка": (165, 31, 3.6, 0, 45),
        "Рис": (344, 7, 1, 78, 10),
        "Брокколи": (34, 2.8, 0.4, 7, 25),
        "Яйцо": (155, 13, 11, 1.1, 12),
    }
    for name in names:
        kcal, p, f, c, price = specs[name]
        session.add(
            Ingredient(
                canonical_name=name,
                normalized_name=canonical_key(name),
                default_unit="g" if name != "Яйцо" else "piece",
                calories_per_100g=Decimal(str(kcal)),
                protein_per_100g=Decimal(str(p)),
                fat_per_100g=Decimal(str(f)),
                carbohydrate_per_100g=Decimal(str(c)),
                reference_price_per_100g=Decimal(str(price)),
                currency="RUB",
                grams_per_piece=Decimal("55") if name == "Яйцо" else None,
                source="seed",
                is_active=True,
            )
        )


async def _seed_commit(session, *names: str) -> None:
    _seed(session, *names)
    await session.commit()


@pytest.mark.asyncio
async def test_manual_quick_add_search_and_totals(client: AsyncClient, session, services):
    await _seed_commit(session, "Куриная грудка", "Рис")
    tokens = await _register(client, "diary21@example.com")
    headers = _auth(tokens)
    today = date.today().isoformat()

    manual = await client.post(
        f"{API}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": today,
            "meal_type": "breakfast",
            "source": "manual",
            "description": "Омлет",
            "calories_kcal": 300,
            "protein_g": 20,
            "fat_g": 18,
            "carbohydrate_g": 5,
        },
    )
    assert manual.status_code == 201, manual.text

    quick = await client.post(
        f"{API}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": today,
            "meal_type": "snack",
            "source": "quick_add",
            "description": "Кофе",
            "calories_kcal": 50,
        },
    )
    assert quick.status_code == 201, quick.text

    search = await client.get(
        f"{API}/nutrition/foods/search", headers=headers, params={"q": "кури"}
    )
    assert search.status_code == 200
    hits = search.json()
    assert hits
    ingredient_id = hits[0]["ingredient_id"]

    calc = await client.post(
        f"{API}/nutrition/foods/calculate",
        headers=headers,
        json={"ingredient_id": ingredient_id, "quantity_g": 200},
    )
    assert calc.status_code == 200
    assert calc.json()["calories_kcal"] == 330

    logged = await client.post(
        f"{API}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": today,
            "meal_type": "lunch",
            "source": "search",
            "ingredient_id": ingredient_id,
            "quantity_g": 200,
            "description": "Куриная грудка",
        },
    )
    assert logged.status_code == 201, logged.text
    assert logged.json()["calories_kcal"] == 330

    day = await client.get(
        f"{API}/nutrition/diary/day", headers=headers, params={"date": today}
    )
    assert day.status_code == 200
    assert day.json()["totals"]["calories_kcal"] == 300 + 50 + 330

    history = await client.get(
        f"{API}/nutrition/diary/history", headers=headers, params={"days": 3}
    )
    assert history.status_code == 200
    assert len(history.json()) == 3

    log_id = logged.json()["id"]
    patched = await client.patch(
        f"{API}/nutrition/logs/{log_id}",
        headers=headers,
        json={"quantity_g": 100, "ingredient_id": ingredient_id},
    )
    assert patched.status_code == 200
    assert patched.json()["calories_kcal"] == 165

    dup = await client.post(
        f"{API}/nutrition/logs/{log_id}/duplicate", headers=headers
    )
    assert dup.status_code == 201

    deleted = await client.delete(
        f"{API}/nutrition/logs/{dup.json()['id']}", headers=headers
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_photo_analyze_confirm_recalc(client: AsyncClient, session, services, app):
    await _seed_commit(session, "Куриная грудка", "Рис", "Брокколи")
    tokens = await _register(client, "photo21@example.com")
    headers = _auth(tokens)

    mock = MockOpenAIVisionProvider(
        [
            VisionFoodAnalysisResult(
                items=[
                    VisionFoodItem(
                        name="куриная грудка",
                        estimated_grams=200,
                        confidence=0.92,
                        notes=None,
                    ),
                    VisionFoodItem(
                        name="рис",
                        estimated_grams=150,
                        confidence=0.8,
                        notes=None,
                    ),
                    VisionFoodItem(
                        name="mystery goo",
                        estimated_grams=50,
                        confidence=0.2,
                        notes="uncertain",
                    ),
                ],
                overall_confidence=0.7,
                warnings=[],
                model="mock-vision",
                duration_ms=5,
            )
        ]
    )
    app.state.vision_provider = mock

    # Minimal JPEG-ish bytes (downscale tolerates garbage via PIL fail-open).
    image = b"\xff\xd8\xff\xe0" + b"0" * 200
    analyze = await client.post(
        f"{API}/nutrition/photo/analyze",
        headers=headers,
        files={"file": ("meal.jpg", BytesIO(image), "image/jpeg")},
    )
    assert analyze.status_code == 200, analyze.text
    body = analyze.json()
    assert len(body["items"]) == 3
    chicken = next(i for i in body["items"] if i["matched"] and "Курин" in (i["canonical_name"] or ""))
    assert chicken["calories_kcal"] == 330
    assert any(i["low_confidence"] for i in body["items"])
    assert len(mock.calls) == 1

    confirm = await client.post(
        f"{API}/nutrition/photo/confirm",
        headers={**headers, "Idempotency-Key": "photo-confirm-1"},
        json={
            "logged_on": date.today().isoformat(),
            "meal_type": "lunch",
            "items": [
                {
                    "ingredient_id": chicken["ingredient_id"],
                    "description": chicken["canonical_name"],
                    "quantity_g": 180,
                    "meal_type": "lunch",
                }
            ],
        },
    )
    assert confirm.status_code == 201, confirm.text
    assert confirm.json()[0]["source"] == "photo_ai"
    assert confirm.json()[0]["calories_kcal"] == int(165 * 1.8)

    # Idempotent retry
    again = await client.post(
        f"{API}/nutrition/photo/confirm",
        headers={**headers, "Idempotency-Key": "photo-confirm-1"},
        json={
            "logged_on": date.today().isoformat(),
            "meal_type": "lunch",
            "items": [
                {
                    "ingredient_id": chicken["ingredient_id"],
                    "description": chicken["canonical_name"],
                    "quantity_g": 180,
                    "meal_type": "lunch",
                }
            ],
        },
    )
    assert again.status_code == 201
    listed = await client.get(
        f"{API}/nutrition/logs",
        headers=headers,
        params={"date": date.today().isoformat()},
    )
    photo_rows = [r for r in listed.json() if r["source"] == "photo_ai"]
    assert len(photo_rows) == 1


@pytest.mark.asyncio
async def test_photo_ownership_isolation(client: AsyncClient, session, app):
    await _seed_commit(session, "Куриная грудка")
    a = await _register(client, "a21@example.com")
    b = await _register(client, "b21@example.com")
    today = date.today().isoformat()
    created = await client.post(
        f"{API}/nutrition/logs",
        headers=_auth(a),
        json={
            "logged_on": today,
            "meal_type": "lunch",
            "source": "manual",
            "description": "Secret",
            "calories_kcal": 100,
            "protein_g": 1,
            "fat_g": 1,
            "carbohydrate_g": 1,
        },
    )
    log_id = created.json()["id"]
    denied = await client.delete(
        f"{API}/nutrition/logs/{log_id}", headers=_auth(b)
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_match_and_nutrition_helpers(session):
    await _seed_commit(session, "Куриная грудка")
    catalog = await RecipeRepository(session).active_catalog()
    matched_ru = match_food_name(
        "Куриная грудка", catalog, estimated_grams=100, confidence=0.9
    )
    assert matched_ru.matched
    assert matched_ru.calories_kcal == 165
    matched_en = match_food_name(
        "chicken breast", catalog, estimated_grams=100, confidence=0.9
    )
    assert matched_en.matched
    ing = catalog[canonical_key("Куриная грудка")]
    macros = nutrition_for_grams(ing, Decimal("250"))
    assert macros["calories_kcal"] == 412
