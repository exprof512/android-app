from __future__ import annotations

from uuid import uuid4

import jwt
import pytest

from app.auth.errors import InvalidToken
from app.auth.tokens import (
    ACCESS_TOKEN_TYPE,
    JWT_ALGORITHM,
    REFRESH_TOKEN_TYPE,
    TokenService,
)

SECRET = "unit-test-signing-key-with-enough-entropy"


def build_service() -> TokenService:
    return TokenService(secret=SECRET, access_ttl_seconds=900, refresh_ttl_days=30)


def test_access_token_round_trip() -> None:
    service = build_service()
    user_id = uuid4()

    issued = service.create_access_token(user_id)
    claims = service.decode(issued.token, expected_type=ACCESS_TOKEN_TYPE)

    assert claims.user_id == user_id
    assert claims.token_id == issued.token_id
    assert claims.token_type == ACCESS_TOKEN_TYPE
    assert issued.expires_in == 900


def test_refresh_token_carries_its_family() -> None:
    service = build_service()
    family_id = uuid4()

    issued = service.create_refresh_token(uuid4(), family_id=family_id)
    claims = service.decode(issued.token, expected_type=REFRESH_TOKEN_TYPE)

    assert issued.family_id == family_id
    assert claims.family_id == family_id


def test_new_refresh_token_starts_a_new_family() -> None:
    service = build_service()

    first = service.create_refresh_token(uuid4())
    second = service.create_refresh_token(uuid4())

    assert first.family_id != second.family_id


def test_expired_token_is_rejected() -> None:
    service = build_service()

    issued = service.create_access_token(uuid4(), ttl_seconds=-1)

    with pytest.raises(InvalidToken):
        service.decode(issued.token, expected_type=ACCESS_TOKEN_TYPE)


def test_token_type_is_enforced() -> None:
    service = build_service()
    refresh = service.create_refresh_token(uuid4())
    access = service.create_access_token(uuid4())

    with pytest.raises(InvalidToken):
        service.decode(refresh.token, expected_type=ACCESS_TOKEN_TYPE)
    with pytest.raises(InvalidToken):
        service.decode(access.token, expected_type=REFRESH_TOKEN_TYPE)


def test_token_signed_with_another_secret_is_rejected() -> None:
    service = build_service()
    foreign = TokenService(
        secret="another-signing-key-with-enough-entropy",
        access_ttl_seconds=900,
        refresh_ttl_days=30,
    )

    issued = foreign.create_access_token(uuid4())

    with pytest.raises(InvalidToken):
        service.decode(issued.token, expected_type=ACCESS_TOKEN_TYPE)


def test_unsigned_token_is_rejected() -> None:
    service = build_service()
    forged = jwt.encode({"sub": str(uuid4())}, key="", algorithm="none")

    with pytest.raises(InvalidToken):
        service.decode(forged, expected_type=ACCESS_TOKEN_TYPE)


def test_token_without_required_claims_is_rejected() -> None:
    service = build_service()
    incomplete = jwt.encode({"sub": str(uuid4())}, SECRET, algorithm=JWT_ALGORITHM)

    with pytest.raises(InvalidToken):
        service.decode(incomplete, expected_type=ACCESS_TOKEN_TYPE)


def test_garbage_token_is_rejected() -> None:
    service = build_service()

    with pytest.raises(InvalidToken):
        service.decode("not.a.jwt", expected_type=ACCESS_TOKEN_TYPE)


def test_token_hash_is_a_sha256_digest() -> None:
    issued = build_service().create_refresh_token(uuid4())

    digest = TokenService.hash_token(issued.token)

    assert len(digest) == 64
    assert digest != issued.token
    assert digest == TokenService.hash_token(issued.token)


def test_empty_secret_is_refused() -> None:
    with pytest.raises(ValueError):
        TokenService(secret="", access_ttl_seconds=900, refresh_ttl_days=30)
