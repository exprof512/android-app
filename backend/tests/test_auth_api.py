from __future__ import annotations

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from app.auth.tokens import TokenService
from app.core.services import Services
from tests.conftest import API_PREFIX, TEST_PASSWORD


async def register(
    client: AsyncClient, email: str, password: str = TEST_PASSWORD, **extra: object
) -> dict:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": email, "password": password, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_returns_token_pair_and_safe_user(
    client: AsyncClient, session: AsyncSession
) -> None:
    body = await register(client, "Anna@Example.com", accepted_terms_at="2026-09-18T17:00:00Z")

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == "anna@example.com"
    assert body["user"]["tier"] == "free"
    assert "password" not in body and "password_hash" not in str(body)
    assert TEST_PASSWORD not in str(body)

    user = (await session.execute(select(User))).scalar_one()
    assert user.email == "anna@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert user.locale == "ru-RU"
    assert user.accepted_terms_at is not None


async def test_register_persists_only_the_refresh_token_hash(
    client: AsyncClient, session: AsyncSession
) -> None:
    body = await register(client, "anna@example.com")

    stored = (await session.execute(select(RefreshToken))).scalar_one()
    assert stored.token_hash == TokenService.hash_token(body["refresh_token"])
    assert stored.revoked_at is None
    assert stored.replaced_by_id is None
    assert stored.user_id == UUID(body["user"]["id"])


async def test_register_rejects_a_duplicate_email_case_insensitively(
    client: AsyncClient,
) -> None:
    await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": "ANNA@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"
    assert response.json()["error"]["request_id"]


async def test_register_validates_the_password_length(client: AsyncClient) -> None:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": "anna@example.com", "password": "short"},
    )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"] == [{"field": "password", "reason": "string_too_short"}]


async def test_register_validates_the_email(client: AsyncClient) -> None:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": "not-an-email", "password": TEST_PASSWORD},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "email"


async def test_login_issues_a_new_session(client: AsyncClient, session: AsyncSession) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "ANNA@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["refresh_token"] != registered["refresh_token"]
    assert body["user"]["id"] == registered["user"]["id"]

    families = {
        token.family_id for token in (await session.execute(select(RefreshToken))).scalars()
    }
    assert len(families) == 2


async def test_login_with_a_wrong_password_is_unauthorized(client: AsyncClient) -> None:
    await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "anna@example.com", "password": "another password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_login_does_not_reveal_whether_the_email_exists(client: AsyncClient) -> None:
    await register(client, "anna@example.com")

    known = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "anna@example.com", "password": "another password"},
    )
    unknown = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "nobody@example.com", "password": "another password"},
    )

    assert known.status_code == unknown.status_code == 401
    assert known.json()["error"]["code"] == unknown.json()["error"]["code"]
    assert known.json()["error"]["message"] == unknown.json()["error"]["message"]


async def test_login_is_refused_for_a_disabled_account(
    client: AsyncClient, session: AsyncSession
) -> None:
    await register(client, "anna@example.com")
    user = (await session.execute(select(User))).scalar_one()
    user.is_active = False
    await session.commit()

    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "anna@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_disabled"


async def test_refresh_rotates_the_token_and_keeps_the_family(
    client: AsyncClient, session: AsyncSession
) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != registered["refresh_token"]
    assert rotated["access_token"] != registered["access_token"]

    tokens = list((await session.execute(select(RefreshToken))).scalars())
    assert len(tokens) == 2
    previous = next(
        token
        for token in tokens
        if token.token_hash == TokenService.hash_token(registered["refresh_token"])
    )
    current = next(
        token
        for token in tokens
        if token.token_hash == TokenService.hash_token(rotated["refresh_token"])
    )
    assert previous.revoked_at is not None
    assert previous.replaced_by_id == current.id
    assert current.family_id == previous.family_id
    assert current.revoked_at is None


async def test_reusing_a_rotated_refresh_token_revokes_the_family(
    client: AsyncClient, session: AsyncSession
) -> None:
    registered = await register(client, "anna@example.com")
    rotated = (
        await client.post(
            f"{API_PREFIX}/auth/refresh",
            json={"refresh_token": registered["refresh_token"]},
        )
    ).json()

    reused = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "invalid_token"

    after_breach = await client.post(
        f"{API_PREFIX}/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert after_breach.status_code == 401

    assert all(
        token.revoked_at is not None
        for token in (await session.execute(select(RefreshToken))).scalars()
    )


async def test_refresh_rejects_an_expired_token(
    client: AsyncClient, session: AsyncSession, services: Services
) -> None:
    registered = await register(client, "anna@example.com")
    user_id = UUID(registered["user"]["id"])
    expired = services.tokens.create_refresh_token(user_id, ttl_seconds=-60)
    session.add(
        RefreshToken(
            id=expired.token_id,
            user_id=user_id,
            token_hash=TokenService.hash_token(expired.token),
            family_id=expired.family_id,
            expires_at=expired.expires_at,
        )
    )
    await session.commit()

    response = await client.post(
        f"{API_PREFIX}/auth/refresh", json={"refresh_token": expired.token}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_refresh_rejects_an_unknown_token(
    client: AsyncClient, services: Services
) -> None:
    await register(client, "anna@example.com")
    stranger = services.tokens.create_refresh_token(UUID(int=7))

    response = await client.post(
        f"{API_PREFIX}/auth/refresh", json={"refresh_token": stranger.token}
    )

    assert response.status_code == 401


async def test_refresh_rejects_an_access_token(client: AsyncClient) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": registered["access_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_current_user_returns_a_safe_summary(client: AsyncClient) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == registered["user"]["id"]
    assert body["email"] == "anna@example.com"
    assert body["tier"] == "free"
    assert body["is_active"] is True
    assert "password_hash" not in body


async def test_current_user_requires_a_bearer_token(client: AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_current_user_rejects_a_refresh_token(client: AsyncClient) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": f"Bearer {registered['refresh_token']}"},
    )

    assert response.status_code == 401


async def test_current_user_rejects_a_tampered_token(client: AsyncClient) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": f"Bearer {registered['access_token']}x"},
    )

    assert response.status_code == 401


async def test_current_user_is_refused_after_the_account_is_disabled(
    client: AsyncClient, session: AsyncSession
) -> None:
    registered = await register(client, "anna@example.com")
    user = (await session.execute(select(User))).scalar_one()
    user.is_active = False
    await session.commit()

    response = await client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_disabled"


async def test_logout_revokes_the_session(
    client: AsyncClient, session: AsyncSession
) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/logout",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
        json={"refresh_token": registered["refresh_token"]},
    )

    assert response.status_code == 204
    stored = (await session.execute(select(RefreshToken))).scalar_one()
    assert stored.revoked_at is not None

    reuse = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )
    assert reuse.status_code == 401


async def test_logout_requires_authentication(client: AsyncClient) -> None:
    registered = await register(client, "anna@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/logout",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert response.status_code == 401


async def test_logout_cannot_revoke_another_users_session(client: AsyncClient) -> None:
    anna = await register(client, "anna@example.com")
    boris = await register(client, "boris@example.com")

    response = await client.post(
        f"{API_PREFIX}/auth/logout",
        headers={"Authorization": f"Bearer {anna['access_token']}"},
        json={"refresh_token": boris["refresh_token"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ownership_denied"

    still_valid = await client.post(
        f"{API_PREFIX}/auth/refresh", json={"refresh_token": boris["refresh_token"]}
    )
    assert still_valid.status_code == 200


async def test_unknown_route_under_the_api_prefix_uses_the_error_envelope(
    client: AsyncClient,
) -> None:
    response = await client.get(f"{API_PREFIX}/auth/unknown")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
