"""Phase 22: planned meals must never inflate consumed nutrition."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import auth, register


def _macros_to_kcal(protein_g: float, fat_g: float, carbs_g: float) -> float:
    return protein_g * 4 + carbs_g * 4 + fat_g * 9


@pytest.mark.asyncio
async def test_planned_meals_do_not_count_as_consumed(client: AsyncClient, ready_user):
    tokens, _provider = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text
    items = generated.json()["items"]
    day_items = [i for i in items if i["date"] == START.isoformat()]
    assert len(day_items) >= 3

    breakfast, lunch, dinner = day_items[0], day_items[1], day_items[2]
    breakfast_kcal = breakfast["nutrition"]["calories_kcal"]
    lunch_kcal = lunch["nutrition"]["calories_kcal"]
    dinner_kcal = dinner["nutrition"]["calories_kcal"]

    today0 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today0.status_code == 200, today0.text
    progress0 = today0.json()["day_progress"]
    assert progress0["consumed_kcal"] == 0
    assert progress0["from_plan_kcal"] == 0
    assert progress0["from_diary_kcal"] == 0
    assert progress0["planned_remaining_kcal"] == sum(
        i["nutrition"]["calories_kcal"] for i in day_items
    )
    assert progress0["over_target_kcal"] == 0
    assert progress0["remaining_kcal"] == progress0["target_kcal"]

    # Eat breakfast only.
    eaten = await client.post(
        f"{API_PREFIX}/meal-plan-items/{breakfast['id']}/complete",
        headers=headers,
        params={"completed": True},
    )
    assert eaten.status_code == 200, eaten.text

    today1 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress1 = today1.json()["day_progress"]
    assert progress1["completed_meals"] == 1
    assert progress1["consumed_kcal"] == breakfast_kcal
    assert progress1["from_plan_kcal"] == breakfast_kcal
    assert progress1["consumed_kcal"] != breakfast_kcal + lunch_kcal + dinner_kcal
    assert progress1["planned_remaining_kcal"] == sum(
        i["nutrition"]["calories_kcal"] for i in day_items[1:]
    )

    # Skip dinner — still only breakfast in consumed.
    skipped = await client.post(
        f"{API_PREFIX}/meal-plan-items/{dinner['id']}/skip",
        headers=headers,
        params={"skipped": True},
    )
    assert skipped.status_code == 200, skipped.text

    today2 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress2 = today2.json()["day_progress"]
    assert progress2["consumed_kcal"] == breakfast_kcal
    assert progress2["skipped_meals"] == 1

    # Eat lunch → breakfast + lunch.
    eaten_lunch = await client.post(
        f"{API_PREFIX}/meal-plan-items/{lunch['id']}/complete",
        headers=headers,
        params={"completed": True},
    )
    assert eaten_lunch.status_code == 200, eaten_lunch.text

    today3 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress3 = today3.json()["day_progress"]
    assert progress3["consumed_kcal"] == breakfast_kcal + lunch_kcal

    # Idempotent complete — still one log / same total.
    await client.post(
        f"{API_PREFIX}/meal-plan-items/{lunch['id']}/complete",
        headers=headers,
        params={"completed": True},
    )
    today4 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today4.json()["day_progress"]["consumed_kcal"] == breakfast_kcal + lunch_kcal

    # Uncomplete breakfast → only lunch remains.
    await client.post(
        f"{API_PREFIX}/meal-plan-items/{breakfast['id']}/complete",
        headers=headers,
        params={"completed": False},
    )
    today5 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today5.json()["day_progress"]["consumed_kcal"] == lunch_kcal

    await client.post(
        f"{API_PREFIX}/meal-plan-items/{lunch['id']}/complete",
        headers=headers,
        params={"completed": False},
    )
    today6 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today6.json()["day_progress"]["consumed_kcal"] == 0


@pytest.mark.asyncio
async def test_diary_logs_count_separately_from_planned(
    client: AsyncClient, ready_user
):
    tokens, _provider = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text
    breakfast = generated.json()["items"][0]
    breakfast_kcal = breakfast["nutrition"]["calories_kcal"]

    await client.post(
        f"{API_PREFIX}/meal-plan-items/{breakfast['id']}/complete",
        headers=headers,
        params={"completed": True},
    )

    manual = await client.post(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": START.isoformat(),
            "meal_type": "snack",
            "source": "manual",
            "description": "Яблоко",
            "calories_kcal": 95,
            "protein_g": 0.5,
            "fat_g": 0.3,
            "carbohydrate_g": 25.0,
        },
    )
    assert manual.status_code == 201, manual.text

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress = today.json()["day_progress"]
    assert progress["from_plan_kcal"] == breakfast_kcal
    assert progress["from_diary_kcal"] == 95
    assert progress["consumed_kcal"] == breakfast_kcal + 95


@pytest.mark.asyncio
async def test_over_target_when_consumed_exceeds_goal(client: AsyncClient, ready_user):
    tokens, _provider = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201
    today0 = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    target = today0.json()["day_progress"]["target_kcal"]

    await client.post(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": START.isoformat(),
            "meal_type": "snack",
            "source": "manual",
            "description": "Большая порция",
            "calories_kcal": target + 140,
            "protein_g": 10,
            "fat_g": 10,
            "carbohydrate_g": 10,
        },
    )
    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress = today.json()["day_progress"]
    assert progress["consumed_kcal"] == target + 140
    assert progress["remaining_kcal"] == 0
    assert progress["over_target_kcal"] == 140


@pytest.mark.asyncio
async def test_recipe_display_name_strips_date_suffix(client: AsyncClient, ready_user):
    tokens, _provider = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text
    import re

    date_suffix = re.compile(r"\(\d{4}-\d{2}-\d{2}\)\s*$")
    for item in generated.json()["items"]:
        name = item["recipe"]["name"]
        assert not date_suffix.search(name), name


@pytest.mark.asyncio
async def test_macro_calorie_sanity_diagnostic():
    """Diagnostic only — do not replace authoritative calories."""
    protein, fat, carbs = 25.0, 10.0, 40.0
    derived = _macros_to_kcal(protein, fat, carbs)
    authoritative = 350
    # Acceptable rounding band (~15%).
    assert abs(derived - authoritative) / authoritative < 0.15


@pytest.mark.asyncio
async def test_midnight_boundary_logged_on_local_date(client: AsyncClient):
    tokens = await register(client, "tz-phase22@example.com")
    headers = auth(tokens)
    today = date.today()
    created = await client.post(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": today.isoformat(),
            "meal_type": "snack",
            "source": "manual",
            "description": "Поздний перекус",
            "calories_kcal": 120,
            "protein_g": 5,
            "fat_g": 2,
            "carbohydrate_g": 15,
        },
    )
    assert created.status_code == 201, created.text

    logs_today = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"date": today.isoformat()},
    )
    assert any(row["calories_kcal"] == 120 for row in logs_today.json())

    from datetime import timedelta

    yesterday = today - timedelta(days=1)
    logs_y = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"date": yesterday.isoformat()},
    )
    assert not any(row["id"] == created.json()["id"] for row in logs_y.json())
