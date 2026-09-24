from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from tests.conftest import API_PREFIX, TEST_PASSWORD

PROFILE_PAYLOAD: dict[str, Any] = {
    "sex": "female",
    "age_years": 31,
    "height_cm": 168,
    "current_weight_kg": 72.4,
    "target_weight_kg": 64,
    "activity_level": "moderate",
    "goal_type": "lose_weight",
    "desired_weekly_change_kg": 0.4,
    "meals_per_day": 4,
    "daily_calorie_mode": "auto",
    "grocery_budget_weekly": 6500,
    "currency": "RUB",
    "max_cook_time_minutes": 35,
    "household_size": 2,
    "timezone": "Europe/Moscow",
    "liked_foods": ["гречка", "лосось"],
    "disliked_foods": ["сельдерей"],
    "excluded_foods": ["свинина"],
    "allergies": ["арахис"],
    "available_products": [{"name": "яйца", "quantity": 10, "unit": "piece"}],
}
DISCLAIMER = "Расчёты приблизительны и не заменяют врача или диетолога."


async def register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_registration_creates_one_empty_profile(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")

    response = await client.get(f"{API_PREFIX}/profile", headers=auth(tokens))

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["sex"] is None
    assert body["profile"]["current_weight_kg"] is None
    assert body["goal"] is None
    assert body["preferences"] == {"liked_foods": [], "disliked_foods": []}
    assert body["restrictions"] == {"excluded_foods": [], "allergies": []}
    assert body["available_products"] == []
    assert body["warnings"] == []

    profiles = await session.scalar(select(func.count()).select_from(UserProfile))
    assert profiles == 1


async def test_update_profile_persists_questionnaire_and_targets(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")

    response = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=PROFILE_PAYLOAD
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["profile"]["sex"] == "female"
    assert body["profile"]["current_weight_kg"] == 72.4
    assert body["profile"]["meals_per_day"] == 4
    assert body["profile"]["grocery_budget_weekly"] == 6500.0
    assert body["profile"]["currency"] == "RUB"
    assert body["goal"]["goal_type"] == "lose_weight"
    assert body["goal"]["calorie_target_kcal"] == 1820
    assert body["goal"]["bmr_kcal"] == 1458
    assert body["goal"]["tdee_kcal"] == 2260
    assert body["goal"]["safety_floor_kcal"] == 1200
    assert body["goal"]["start_weight_kg"] == 72.4
    assert body["goal"]["macro_targets_g"] == {
        "protein": 116,
        "fat": 61,
        "carbohydrate": 203,
    }
    assert body["preferences"]["liked_foods"] == ["гречка", "лосось"]
    assert body["restrictions"]["allergies"] == ["арахис"]
    assert body["available_products"] == [
        {"name": "яйца", "quantity": 10.0, "unit": "piece", "expires_on": None}
    ]
    assert DISCLAIMER in body["warnings"]

    goal = (await session.execute(select(Goal))).scalar_one()
    assert goal.status == "active"
    assert goal.calorie_target_kcal == 1820
    profile = (await session.execute(select(UserProfile))).scalar_one()
    assert profile.active_goal_id == goal.id


async def test_profile_round_trips_through_get(client: AsyncClient) -> None:
    tokens = await register(client, "anna@example.com")
    updated = (
        await client.put(
            f"{API_PREFIX}/profile", headers=auth(tokens), json=PROFILE_PAYLOAD
        )
    ).json()

    fetched = (await client.get(f"{API_PREFIX}/profile", headers=auth(tokens))).json()

    assert fetched["profile"] == updated["profile"]
    assert fetched["goal"] == updated["goal"]
    assert fetched["preferences"] == updated["preferences"]
    assert fetched["available_products"] == updated["available_products"]
    assert fetched["warnings"] == [DISCLAIMER]


async def test_update_replaces_lists_and_keeps_one_active_goal(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")
    await client.put(f"{API_PREFIX}/profile", headers=auth(tokens), json=PROFILE_PAYLOAD)

    second = dict(PROFILE_PAYLOAD)
    second.update(
        {
            "current_weight_kg": 71.0,
            "liked_foods": ["киноа"],
            "disliked_foods": [],
            "excluded_foods": [],
            "allergies": ["молоко"],
            "available_products": [{"name": "рис", "quantity": 2, "unit": "kg"}],
        }
    )
    response = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=second
    )

    assert response.status_code == 200
    body = response.json()
    assert body["preferences"] == {"liked_foods": ["киноа"], "disliked_foods": []}
    assert body["restrictions"] == {"excluded_foods": [], "allergies": ["молоко"]}
    assert [item["name"] for item in body["available_products"]] == ["рис"]
    # The goal keeps the weight it started with.
    assert body["goal"]["start_weight_kg"] == 72.4
    assert body["profile"]["current_weight_kg"] == 71.0

    assert await session.scalar(select(func.count()).select_from(Goal)) == 1
    assert await session.scalar(select(func.count()).select_from(FoodPreference)) == 1
    assert await session.scalar(select(func.count()).select_from(FoodRestriction)) == 1
    assert await session.scalar(select(func.count()).select_from(AvailableProduct)) == 1


async def test_food_names_are_normalized_and_deduplicated(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")
    payload = dict(PROFILE_PAYLOAD)
    payload["liked_foods"] = ["Гречка", "  гречка ", "гречка", "Лосось"]
    payload["allergies"] = ["Арахис", "арахис"]

    body = (
        await client.put(f"{API_PREFIX}/profile", headers=auth(tokens), json=payload)
    ).json()

    assert body["preferences"]["liked_foods"] == ["Гречка", "Лосось"]
    assert body["restrictions"]["allergies"] == ["Арахис"]
    liked = list(
        (
            await session.execute(
                select(FoodPreference).where(FoodPreference.preference_type == "liked")
            )
        ).scalars()
    )
    assert sorted(item.normalized_food_name for item in liked) == ["гречка", "лосось"]


async def test_pantry_merges_the_same_product_and_unit(client: AsyncClient) -> None:
    tokens = await register(client, "anna@example.com")
    payload = dict(PROFILE_PAYLOAD)
    payload["available_products"] = [
        {"name": "Яйца", "quantity": 6, "unit": "piece"},
        {"name": "яйца", "quantity": 4, "unit": "piece"},
        {"name": "яйца", "quantity": 1, "unit": "pack"},
    ]

    body = (
        await client.put(f"{API_PREFIX}/profile", headers=auth(tokens), json=payload)
    ).json()

    merged = {(item["unit"], item["quantity"]) for item in body["available_products"]}
    assert merged == {("piece", 10.0), ("pack", 1.0)}


async def test_rejected_goal_writes_nothing(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")
    payload = dict(PROFILE_PAYLOAD)
    payload["desired_weekly_change_kg"] = 1.0
    payload["target_weight_kg"] = 45

    response = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=payload
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "nutrition_validation_error"
    assert error["details"] == [
        {"field": "target_weight_kg", "reason": "below_safe_bmi"}
    ]
    assert error["request_id"]

    assert await session.scalar(select(func.count()).select_from(Goal)) == 0
    profile = (await session.execute(select(UserProfile))).scalar_one()
    assert profile.sex is None


async def test_schema_violations_use_the_validation_envelope(client: AsyncClient) -> None:
    tokens = await register(client, "anna@example.com")
    payload = dict(PROFILE_PAYLOAD)
    payload["meals_per_day"] = 12
    payload["activity_level"] = "extreme"

    response = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=payload
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert fields == {"meals_per_day", "activity_level"}


async def test_calorie_floor_is_reported_in_the_goal(client: AsyncClient) -> None:
    tokens = await register(client, "anna@example.com")
    payload = dict(PROFILE_PAYLOAD)
    payload["daily_calorie_mode"] = "target"
    payload["daily_calorie_value"] = 900

    body = (
        await client.put(f"{API_PREFIX}/profile", headers=auth(tokens), json=payload)
    ).json()

    assert body["goal"]["calorie_target_kcal"] == 1200
    assert body["goal"]["safety_floor_kcal"] == 1200
    assert any("1200" in warning for warning in body["warnings"])
    assert body["warnings"][0] == DISCLAIMER


async def test_calculate_target_previews_without_saving(
    client: AsyncClient, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")
    payload = {
        key: PROFILE_PAYLOAD[key]
        for key in (
            "sex",
            "age_years",
            "height_cm",
            "current_weight_kg",
            "target_weight_kg",
            "activity_level",
            "goal_type",
            "desired_weekly_change_kg",
        )
    }

    response = await client.post(
        f"{API_PREFIX}/profile/calculate-target", headers=auth(tokens), json=payload
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "bmr_kcal": 1458,
        "tdee_kcal": 2260,
        "recommended_calorie_target_kcal": 1820,
        "applied_safety_floor_kcal": 1200,
        "macro_targets_g": {"protein": 116, "fat": 61, "carbohydrate": 203},
        "warnings": [DISCLAIMER],
    }

    assert await session.scalar(select(func.count()).select_from(Goal)) == 0
    profile = (await session.execute(select(UserProfile))).scalar_one()
    assert profile.current_weight_kg is None


async def test_calculate_target_allows_pace_within_engine_cap(client: AsyncClient) -> None:
    """Schema max is 2.0 kg/week; 1.5 must be accepted (engine default cap is 2.0)."""
    tokens = await register(client, "anna@example.com")
    payload = {
        "sex": "male",
        "age_years": 40,
        "height_cm": 180,
        "current_weight_kg": 95,
        "target_weight_kg": 85,
        "activity_level": "light",
        "goal_type": "lose_weight",
        "desired_weekly_change_kg": 1.5,
    }

    response = await client.post(
        f"{API_PREFIX}/profile/calculate-target", headers=auth(tokens), json=payload
    )

    assert response.status_code == 200, response.text
    assert response.json()["recommended_calorie_target_kcal"] > 0


async def test_calculate_target_rejects_pace_above_schema_max(client: AsyncClient) -> None:
    tokens = await register(client, "pace-max@example.com")
    payload = {
        "sex": "male",
        "age_years": 40,
        "height_cm": 180,
        "current_weight_kg": 95,
        "target_weight_kg": 85,
        "activity_level": "light",
        "goal_type": "lose_weight",
        "desired_weekly_change_kg": 2.5,
    }

    response = await client.post(
        f"{API_PREFIX}/profile/calculate-target", headers=auth(tokens), json=payload
    )

    assert response.status_code == 422


async def test_profile_endpoints_require_authentication(client: AsyncClient) -> None:
    read = await client.get(f"{API_PREFIX}/profile")
    write = await client.put(f"{API_PREFIX}/profile", json=PROFILE_PAYLOAD)
    preview = await client.post(f"{API_PREFIX}/profile/calculate-target", json={})

    assert read.status_code == write.status_code == preview.status_code == 401
    assert read.json()["error"]["code"] == "invalid_token"


async def test_one_user_never_sees_another_profile(client: AsyncClient) -> None:
    anna = await register(client, "anna@example.com")
    boris = await register(client, "boris@example.com")
    await client.put(f"{API_PREFIX}/profile", headers=auth(anna), json=PROFILE_PAYLOAD)

    body = (await client.get(f"{API_PREFIX}/profile", headers=auth(boris))).json()

    assert body["profile"]["sex"] is None
    assert body["goal"] is None
    assert body["preferences"]["liked_foods"] == []
    assert body["available_products"] == []
