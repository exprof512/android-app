"""Phase 23 regressions: diary↔plan sync, progress without plan, export water, continuity."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import PROFILE_PAYLOAD, auth, register


@pytest.mark.asyncio
async def test_delete_plan_linked_log_uncompletes_item(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert generated.status_code == 201, generated.text
    item = generated.json()["items"][0]
    item_id = item["id"]

    eaten = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=headers,
        params={"completed": True},
    )
    assert eaten.status_code == 200, eaten.text

    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"logged_on": START.isoformat()},
    )
    assert logs.status_code == 200
    linked = [row for row in logs.json() if row["meal_plan_item_id"] == item_id]
    assert len(linked) == 1

    deleted = await client.delete(
        f"{API_PREFIX}/nutrition/logs/{linked[0]['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    progress = today.json()["day_progress"]
    assert progress["consumed_kcal"] == 0
    assert progress["from_plan_kcal"] == 0
    restored = next(i for i in today.json()["items"] if i["id"] == item_id)
    assert restored["status"] == "planned"
    assert restored["is_completed"] is False


@pytest.mark.asyncio
async def test_duplicate_plan_linked_log_rejected(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1},
    )
    item_id = generated.json()["items"][0]["id"]
    await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=headers,
        params={"completed": True},
    )
    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"logged_on": START.isoformat()},
    )
    log_id = next(
        row["id"] for row in logs.json() if row["meal_plan_item_id"] == item_id
    )
    dup = await client.post(
        f"{API_PREFIX}/nutrition/logs/{log_id}/duplicate",
        headers=headers,
    )
    assert dup.status_code == 422
    assert dup.json()["error"]["code"] == "nutrition_log_validation_error"


@pytest.mark.asyncio
async def test_progress_counts_diary_without_plan(client: AsyncClient):
    tokens = await register(client, f"p23-nopaln-{uuid4().hex[:8]}@example.com")
    headers = auth(tokens)
    profile = await client.put(
        f"{API_PREFIX}/profile",
        headers=headers,
        json=PROFILE_PAYLOAD,
    )
    assert profile.status_code == 200, profile.text

    on_date = date.today().isoformat()
    logged = await client.post(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": on_date,
            "meal_type": "snack",
            "source": "manual",
            "description": "Яблоко",
            "calories_kcal": 95,
            "protein_g": 0.5,
            "fat_g": 0.3,
            "carbohydrate_g": 25,
        },
    )
    assert logged.status_code == 201, logged.text

    summary = await client.get(f"{API_PREFIX}/progress/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    today = summary.json()["today"]
    assert today["consumed_calories_kcal"] == 95


@pytest.mark.asyncio
async def test_replace_completed_syncs_diary_macros(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    headers = auth(tokens)
    generated = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=headers,
        json={"start_date": START.isoformat(), "days": 1, "force": True},
    )
    assert generated.status_code == 201, generated.text
    item = generated.json()["items"][0]
    item_id = item["id"]
    old_kcal = item["nutrition"]["calories_kcal"]

    await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/complete",
        headers=headers,
        params={"completed": True},
    )

    replaced = await client.post(
        f"{API_PREFIX}/meal-plan-items/{item_id}/replace",
        headers={**headers, "Idempotency-Key": f"p23-replace-{item_id}"},
        json={"replace_reason": "other"},
    )
    assert replaced.status_code == 200, replaced.text
    new_item = next(i for i in replaced.json()["items"] if i["id"] == item_id)
    new_kcal = new_item["nutrition"]["calories_kcal"]
    assert new_item["is_completed"] is True
    assert new_item["status"] == "completed"

    logs = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"logged_on": START.isoformat()},
    )
    linked = [row for row in logs.json() if row["meal_plan_item_id"] == item_id]
    assert len(linked) == 1
    assert linked[0]["calories_kcal"] == new_kcal

    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": START.isoformat()},
    )
    assert today.json()["day_progress"]["consumed_kcal"] == new_kcal
    assert today.json()["day_progress"]["consumed_kcal"] != old_kcal + new_kcal


@pytest.mark.asyncio
async def test_export_includes_water_entries(client: AsyncClient, ready_user):
    tokens, _ = ready_user
    headers = auth(tokens)
    added = await client.post(
        f"{API_PREFIX}/water",
        headers=headers,
        json={"amount_ml": 250},
    )
    assert added.status_code in {200, 201}, added.text

    export = await client.get(f"{API_PREFIX}/users/me/export", headers=headers)
    assert export.status_code == 200, export.text
    data = export.json()
    assert data.get("exported_at")
    assert "water_entries" in data
    assert any(e.get("amount_ml") == 250 for e in data["water_entries"])


@pytest.mark.asyncio
async def test_continuity_today_generates_without_force(
    client: AsyncClient, ready_user, session
):
    from tests.test_phase22_plan_continuity import _seed_fallback_ingredients

    tokens, _ = ready_user
    headers = auth(tokens)
    await _seed_fallback_ingredients(session)
    far = date(2030, 1, 6)
    today = await client.get(
        f"{API_PREFIX}/meal-plans/today",
        headers=headers,
        params={"date": far.isoformat()},
    )
    assert today.status_code == 200, today.text
    assert today.json()["items"]
