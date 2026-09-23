"""Phase 19 daily loop: day_progress, complete/skip logs, water, recipes, shopping."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import auth, register


@pytest.mark.asyncio
async def test_today_day_progress_and_week_summary(
    client: AsyncClient, ready_user
):
    tokens, _provider = ready_user
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    assert today.status_code == 200, today.text
    body = today.json()
    progress = body["day_progress"]
    assert progress is not None
    assert progress["planned_meals"] == 4
    assert progress["completed_meals"] == 0
    assert progress["target_kcal"] > 0
    assert progress["remaining_kcal"] == progress["target_kcal"]
    assert progress["next_meal_type"] in {"breakfast", "lunch", "dinner", "snack"}
    assert progress["next_meal_item_id"]
    assert any("Следующий приём" in s for s in progress["suggestions"])
    assert progress["protein"]["remaining_g"] >= 0

    week = await client.get(
        f"{API_PREFIX}/meal-plans/week",
        headers=auth(tokens),
        params={"start_date": START.isoformat()},
    )
    assert week.status_code == 200, week.text
    summary = week.json()["week_summary"]
    assert summary is not None
    assert len(summary["days"]) >= 1
    day0 = summary["days"][0]
    assert day0["date"] == START.isoformat()
    assert day0["status"] == "planned"
    assert day0["planned_meals"] == 4


@pytest.mark.asyncio
async def test_complete_creates_nutrition_log_idempotent(
    client: AsyncClient, ready_user
):
    tokens, _provider = ready_user
    plan = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert plan.status_code == 201, plan.text
    item_id = plan.json()["items"][0]["id"]

    first = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=auth(tokens),
        params={"completed": True},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "completed"
    assert first.json()["is_completed"] is True

    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    assert logs.status_code == 200, logs.text
    tied = [row for row in logs.json() if row["meal_plan_item_id"] == item_id]
    assert len(tied) == 1
    assert tied[0]["source"] == "meal_plan_item"

    second = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=auth(tokens),
        params={"completed": True},
    )
    assert second.status_code == 200, second.text
    logs2 = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    tied2 = [row for row in logs2.json() if row["meal_plan_item_id"] == item_id]
    assert len(tied2) == 1

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    progress = today.json()["day_progress"]
    assert progress["completed_meals"] == 1
    assert progress["consumed_kcal"] > 0

    undone = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=auth(tokens),
        params={"completed": False},
    )
    assert undone.status_code == 200
    assert undone.json()["status"] == "planned"
    logs3 = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    assert not any(row["meal_plan_item_id"] == item_id for row in logs3.json())


@pytest.mark.asyncio
async def test_skip_does_not_consume(client: AsyncClient, ready_user):
    tokens, _provider = ready_user
    plan = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    item_id = plan.json()["items"][0]["id"]

    skipped = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/skip",
        headers=auth(tokens),
        params={"skipped": True},
    )
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["status"] == "skipped"
    assert skipped.json()["is_completed"] is False

    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    assert logs.status_code == 200
    assert not any(row["meal_plan_item_id"] == item_id for row in logs.json())

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=auth(tokens),
        params={"date": START.isoformat()},
    )
    progress = today.json()["day_progress"]
    assert progress["skipped_meals"] == 1
    assert progress["consumed_kcal"] == 0

    restored = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/skip",
        headers=auth(tokens),
        params={"skipped": False},
    )
    assert restored.json()["status"] == "planned"


@pytest.mark.asyncio
async def test_water_add_and_undo(client: AsyncClient):
    tokens = await register(client, "water@example.com")
    headers = auth(tokens)

    added = await client.post(
        f"{API_PREFIX}/water",
        headers=headers,
        json={"amount_ml": 250, "recorded_on": date.today().isoformat()},
    )
    assert added.status_code == 201, added.text
    entry_id = added.json()["id"]

    today = await client.get(f"{API_PREFIX}/water/today", headers=headers)
    assert today.status_code == 200, today.text
    body = today.json()
    assert body["total_ml"] == 250
    assert body["goal_ml"] == 2000
    assert len(body["entries"]) == 1

    undo = await client.delete(f"{API_PREFIX}/water/last", headers=headers)
    assert undo.status_code == 204

    today2 = await client.get(f"{API_PREFIX}/water/today", headers=headers)
    assert today2.json()["total_ml"] == 0

    again = await client.post(
        f"{API_PREFIX}/water",
        headers=headers,
        json={"amount_ml": 300},
    )
    assert again.status_code == 201
    deleted = await client.delete(
        f"{API_PREFIX}/water/{again.json()['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert (await client.get(f"{API_PREFIX}/water/today", headers=headers)).json()[
        "total_ml"
    ] == 0
    missing = await client.delete(f"{API_PREFIX}/water/{entry_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_recipe_search_and_favorites(client: AsyncClient, ready_user):
    tokens, _provider = ready_user
    plan = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    recipe_id = plan.json()["items"][0]["recipe"]["id"]
    recipe_name = plan.json()["items"][0]["recipe"]["name"]

    fav = await client.post(
        f"{API_PREFIX}/recipes/{recipe_id}/favorite", headers=auth(tokens)
    )
    assert fav.status_code == 204

    listed = await client.get(f"{API_PREFIX}/recipes/favorites", headers=auth(tokens))
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == recipe_id for row in listed.json())

    search = await client.get(
        f"{API_PREFIX}/recipes/search",
        headers=auth(tokens),
        params={"q": recipe_name[:4], "max_kcal": 2000},
    )
    assert search.status_code == 200, search.text
    assert any(row["id"] == recipe_id for row in search.json())


@pytest.mark.asyncio
async def test_shopping_estimated_total_and_category(
    client: AsyncClient, ready_user
):
    tokens, _provider = ready_user
    plan = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    meal_plan_id = plan.json()["id"]
    item_id = plan.json()["items"][0]["id"]

    shopping = await client.post(
        f"{API_PREFIX}/shopping-lists/generate",
        headers=auth(tokens),
        json={"meal_plan_id": meal_plan_id, "exclude_available_products": False},
    )
    assert shopping.status_code == 201, shopping.text
    body = shopping.json()
    assert body["stale"] is False
    assert body["plan_fingerprint"]
    assert body["currency"] == "RUB"
    assert body["estimated_total_amount"] is not None
    assert body["estimated_total_amount"] > 0
    categories = {item["category"] for item in body["items"]}
    assert categories & {"vegetables", "meat", "dairy", "grains", "other"}

    replaced = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/replace",
        headers=auth(tokens),
        json={"replace_reason": "more_protein"},
    )
    assert replaced.status_code == 200, replaced.text

    current = await client.get(
        f"{API_PREFIX}/shopping-lists/current",
        headers=auth(tokens),
        params={"meal_plan_id": meal_plan_id},
    )
    assert current.status_code == 200
    assert current.json()["stale"] is True

    rebuilt = await client.post(
        f"{API_PREFIX}/shopping-lists/generate",
        headers=auth(tokens),
        json={"meal_plan_id": meal_plan_id, "exclude_available_products": False},
    )
    assert rebuilt.status_code == 201
    assert rebuilt.json()["stale"] is False
    assert rebuilt.json()["plan_fingerprint"]

    first_item = rebuilt.json()["items"][0]["id"]
    await client.post(
        f"{API_PREFIX}/shopping-list-items/{first_item}/complete",
        headers=auth(tokens),
        params={"completed": True},
    )
    cleared = await client.post(
        f"{API_PREFIX}/shopping-list-items/clear-completed",
        headers=auth(tokens),
    )
    assert cleared.status_code == 200, cleared.text
    assert all(not item["is_completed"] for item in cleared.json()["items"])
    assert first_item not in {i["id"] for i in cleared.json()["items"]}
