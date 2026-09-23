"""Phase 18 account delete/export regression tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX, TEST_PASSWORD
from tests.test_profile_api import PROFILE_PAYLOAD


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": email,
            "password": TEST_PASSWORD,
            "locale": "ru-RU",
            "accepted_terms_at": "2026-09-18T17:00:00Z",
            "platform": "android",
            "app_version": "0.1.0-rc1",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_delete_current_user_success(client: AsyncClient) -> None:
    headers = await _register(client, "p18-delete-ok@example.com")
    deleted = await client.post(
        f"{API_PREFIX}/users/me/delete",
        headers=headers,
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 204
    me = await client.get(f"{API_PREFIX}/users/me", headers=headers)
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_delete_unauthenticated(client: AsyncClient) -> None:
    response = await client.post(
        f"{API_PREFIX}/users/me/delete",
        json={"confirmation": "DELETE"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_invalid_confirmation(client: AsyncClient) -> None:
    headers = await _register(client, "p18-delete-bad@example.com")
    bad = await client.post(
        f"{API_PREFIX}/users/me/delete",
        headers=headers,
        json={"confirmation": "please"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_delete_legacy_header_fallback(client: AsyncClient) -> None:
    headers = await _register(client, "p18-delete-hdr@example.com")
    headers = {**headers, "X-Confirm-Delete": "DELETE"}
    deleted = await client.request(
        "DELETE",
        f"{API_PREFIX}/users/me",
        headers=headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_export_contains_user_owned_data(client: AsyncClient) -> None:
    headers = await _register(client, "p18-export@example.com")
    put = await client.put(
        f"{API_PREFIX}/profile",
        headers=headers,
        json=PROFILE_PAYLOAD,
    )
    assert put.status_code == 200, put.text
    export = await client.get(f"{API_PREFIX}/users/me/export", headers=headers)
    assert export.status_code == 200
    data = export.json()
    assert data.get("exported_at")
    assert data["account"]["email"] == "p18-export@example.com"
    assert "password_hash" not in str(data).lower()
    assert "password" not in data["account"]
    assert data["profile"] is not None
    assert data["profile"]["current_weight_kg"] == 72.4
    assert data["goals"]
    assert "Content-Disposition" in export.headers
