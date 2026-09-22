"""Phase 12 progress API tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX
from tests.test_profile_api import PROFILE_PAYLOAD, auth, register


@pytest.mark.asyncio
async def test_weight_entry_and_progress_summary(client: AsyncClient):
    tokens = await register(client, "progress@example.com")
    profile = await client.put(
        f"{API_PREFIX}/profile", headers=auth(tokens), json=PROFILE_PAYLOAD
    )
    assert profile.status_code == 200, profile.text

    created = await client.post(
        f"{API_PREFIX}/weight-entries",
        headers=auth(tokens),
        json={
            "measured_at": "2026-09-20T07:30:00Z",
            "weight_kg": 71.8,
            "note": "утром",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["weight_kg"] == 71.8

    listed = await client.get(f"{API_PREFIX}/weight-entries", headers=auth(tokens))
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    summary = await client.get(f"{API_PREFIX}/progress/summary", headers=auth(tokens))
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["current_weight_kg"] == 71.8
    assert body["goal_type"] == "lose_weight"
    assert body["disclaimer"]
    assert body["today"] is not None
    assert "гарантир" in body["disclaimer"].lower() or "врач" in body["disclaimer"].lower()
