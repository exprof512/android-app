"""Phase 17 account lifecycle, analytics, diary and admin tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API_PREFIX, TEST_PASSWORD


async def _auth_headers(client: AsyncClient, email: str = "phase17@example.com") -> dict[str, str]:
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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, response.json()


@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient, services) -> None:
    headers, body = await _auth_headers(client, "verify@example.com")
    me = await client.get(f"{API_PREFIX}/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email_verified"] is False
    assert me.json()["consent"]["terms_version"] == "v1"

    peek = await client.get(
        f"{API_PREFIX}/auth/_test/last-email",
        params={"email": "verify@example.com"},
    )
    assert peek.status_code == 200
    token = peek.json()["debug_token"]
    assert token

    ok = await client.post(f"{API_PREFIX}/auth/verify-email", json={"token": token})
    assert ok.status_code == 200

    reused = await client.post(f"{API_PREFIX}/auth/verify-email", json={"token": token})
    assert reused.status_code == 409

    me2 = await client.get(f"{API_PREFIX}/users/me", headers=headers)
    assert me2.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_forgot_reset_password_revokes_sessions(client: AsyncClient) -> None:
    headers, body = await _auth_headers(client, "reset@example.com")
    refresh = body["refresh_token"]

    forgot = await client.post(
        f"{API_PREFIX}/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert forgot.status_code == 200
    # Generic response even for unknown email
    unknown = await client.post(
        f"{API_PREFIX}/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert unknown.status_code == 200
    assert forgot.json()["message"] == unknown.json()["message"]

    peek = await client.get(
        f"{API_PREFIX}/auth/_test/last-email",
        params={"email": "reset@example.com"},
    )
    token = peek.json()["debug_token"]
    assert token

    reset = await client.post(
        f"{API_PREFIX}/auth/reset-password",
        json={"token": token, "new_password": "new-correct-horse-battery"},
    )
    assert reset.status_code == 200

    # Old refresh should fail
    rotated = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert rotated.status_code == 401

    login = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "reset@example.com", "password": "new-correct-horse-battery"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_sessions_list_and_revoke(client: AsyncClient) -> None:
    headers, body = await _auth_headers(client, "sessions@example.com")
    listed = await client.get(f"{API_PREFIX}/users/me/sessions", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
    session_id = listed.json()[0]["id"]

    revoked = await client.delete(
        f"{API_PREFIX}/users/me/sessions/{session_id}", headers=headers
    )
    assert revoked.status_code == 204


@pytest.mark.asyncio
async def test_export_and_delete_account(client: AsyncClient) -> None:
    headers, body = await _auth_headers(client, "delete-me@example.com")
    export = await client.get(f"{API_PREFIX}/users/me/export", headers=headers)
    assert export.status_code == 200
    data = export.json()
    assert "account" in data
    assert "password_hash" not in str(data)
    assert "refresh_token" not in data.get("account", {})

    bad = await client.request(
        "DELETE",
        f"{API_PREFIX}/users/me",
        headers=headers,
        json={"confirmation": "NOPE"},
    )
    assert bad.status_code == 422

    deleted = await client.request(
        "DELETE",
        f"{API_PREFIX}/users/me",
        headers=headers,
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 204

    me = await client.get(f"{API_PREFIX}/users/me", headers=headers)
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_analytics_whitelist_and_pii_rejected(client: AsyncClient) -> None:
    headers, _ = await _auth_headers(client, "analytics@example.com")
    ok = await client.post(
        f"{API_PREFIX}/events",
        headers=headers,
        json={
            "events": [
                {
                    "event_name": "app_opened",
                    "platform": "android",
                    "properties": {"screen": "home"},
                }
            ]
        },
    )
    assert ok.status_code == 200
    assert ok.json()["accepted"] == 1

    bad_event = await client.post(
        f"{API_PREFIX}/events",
        headers=headers,
        json={"events": [{"event_name": "not_a_real_event", "properties": {}}]},
    )
    assert bad_event.status_code == 422

    spoof = await client.post(
        f"{API_PREFIX}/events",
        headers=headers,
        json={
            "events": [
                {
                    "event_name": "login_completed",
                    "properties": {"user_id": "someone-else"},
                }
            ]
        },
    )
    assert spoof.status_code == 422


@pytest.mark.asyncio
async def test_nutrition_log_manual_and_list(client: AsyncClient) -> None:
    headers, _ = await _auth_headers(client, "diary@example.com")
    created = await client.post(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        json={
            "logged_on": "2026-09-23",
            "meal_type": "snack",
            "source": "manual",
            "description": "Йогурт",
            "calories_kcal": 150,
            "protein_g": 10,
            "fat_g": 4,
            "carbohydrate_g": 18,
            "servings": 1,
        },
    )
    assert created.status_code == 201, created.text
    log_id = created.json()["id"]

    listed = await client.get(
        f"{API_PREFIX}/nutrition/logs",
        headers=headers,
        params={"date": "2026-09-23"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client.delete(
        f"{API_PREFIX}/nutrition/logs/{log_id}", headers=headers
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_admin_ai_requires_admin(client: AsyncClient) -> None:
    headers, _ = await _auth_headers(client, "user-not-admin@example.com")
    denied = await client.get(f"{API_PREFIX}/admin/ai/summary", headers=headers)
    assert denied.status_code == 403
