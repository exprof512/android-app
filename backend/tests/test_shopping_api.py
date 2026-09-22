"""Phase 11 shopping list tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX
from tests.test_meal_plan_api import START, ready_user
from tests.test_profile_api import PROFILE_PAYLOAD, auth


@pytest.mark.asyncio
async def test_shopping_generate_merges_and_excludes_pantry(
    client: AsyncClient, ready_user
):
    tokens, _provider = ready_user
    plan = await client.post(
        f"{API_PREFIX}/meal-plans/generate",
        headers=auth(tokens),
        json={"start_date": START.isoformat(), "days": 1},
    )
    assert plan.status_code == 201, plan.text
    meal_plan_id = plan.json()["id"]

    profile = dict(PROFILE_PAYLOAD)
    # Enough rice to fully cover recipe needs so «Рис» disappears from the list.
    profile["available_products"] = [{"name": "Рис", "quantity": 5000, "unit": "g"}]
    updated = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=profile
    )
    assert updated.status_code == 200, updated.text

    response = await client.post(
        f"{API_PREFIX}/shopping-lists/generate",
        headers=auth(tokens),
        json={
            "meal_plan_id": meal_plan_id,
            "exclude_available_products": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["meal_plan_id"] == meal_plan_id
    assert body["items"]
    names = {item["display_name"].lower() for item in body["items"]}
    assert "рис" not in names

    item_id = body["items"][0]["id"]
    done = await client.post(
        f"{API_PREFIX}/shopping-list-items/{item_id}/complete",
        headers=auth(tokens),
        params={"completed": True},
    )
    assert done.status_code == 200, done.text
    assert done.json()["is_completed"] is True

    current = await client.get(
        f"{API_PREFIX}/shopping-lists/current",
        headers=auth(tokens),
        params={"meal_plan_id": meal_plan_id},
    )
    assert current.status_code == 200, current.text
    assert current.json()["id"] == body["id"]
