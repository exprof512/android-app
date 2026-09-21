"""JWT issuing and validation for access and refresh tokens."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.auth.errors import InvalidToken

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
TOKEN_TYPE_CLAIM = "token_type"
FAMILY_CLAIM = "family_id"


@dataclass(frozen=True)
class IssuedAccessToken:
    token: str
    token_id: UUID
    expires_at: datetime
    expires_in: int


@dataclass(frozen=True)
class IssuedRefreshToken:
    token: str
    token_id: UUID
    family_id: UUID
    expires_at: datetime
    expires_in: int


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    token_id: UUID
    token_type: str
    family_id: UUID | None
    expires_at: datetime


class TokenService:
    """Signs short-lived access tokens and rotating refresh tokens."""

    def __init__(
        self, *, secret: str, access_ttl_seconds: int, refresh_ttl_days: int
    ) -> None:
        if not secret:
            raise ValueError("JWT_SECRET must be set before issuing tokens.")
        self._secret = secret
        self._access_ttl_seconds = access_ttl_seconds
        self._refresh_ttl_seconds = refresh_ttl_days * 24 * 60 * 60

    @property
    def access_ttl_seconds(self) -> int:
        return self._access_ttl_seconds

    def create_access_token(
        self, user_id: UUID, *, ttl_seconds: int | None = None
    ) -> IssuedAccessToken:
        ttl = self._access_ttl_seconds if ttl_seconds is None else ttl_seconds
        token_id = uuid4()
        token, expires_at = self._encode(
            user_id=user_id,
            token_id=token_id,
            token_type=ACCESS_TOKEN_TYPE,
            ttl_seconds=ttl,
        )
        return IssuedAccessToken(
            token=token, token_id=token_id, expires_at=expires_at, expires_in=ttl
        )

    def create_refresh_token(
        self,
        user_id: UUID,
        *,
        family_id: UUID | None = None,
        ttl_seconds: int | None = None,
    ) -> IssuedRefreshToken:
        ttl = self._refresh_ttl_seconds if ttl_seconds is None else ttl_seconds
        token_id = uuid4()
        family = family_id or uuid4()
        token, expires_at = self._encode(
            user_id=user_id,
            token_id=token_id,
            token_type=REFRESH_TOKEN_TYPE,
            ttl_seconds=ttl,
            family_id=family,
        )
        return IssuedRefreshToken(
            token=token,
            token_id=token_id,
            family_id=family,
            expires_at=expires_at,
            expires_in=ttl,
        )

    def decode(self, token: str, *, expected_type: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["sub", "jti", "exp", "iat"]},
            )
            if payload[TOKEN_TYPE_CLAIM] != expected_type:
                raise InvalidToken()
            family_raw = payload.get(FAMILY_CLAIM)
            return TokenClaims(
                user_id=UUID(payload["sub"]),
                token_id=UUID(payload["jti"]),
                token_type=payload[TOKEN_TYPE_CLAIM],
                family_id=UUID(family_raw) if family_raw else None,
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (jwt.PyJWTError, AttributeError, KeyError, TypeError, ValueError) as error:
            raise InvalidToken() from error

    @staticmethod
    def hash_token(token: str) -> str:
        """Store only this digest; the token value itself stays out of PostgreSQL."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _encode(
        self,
        *,
        user_id: UUID,
        token_id: UUID,
        token_type: str,
        ttl_seconds: int,
        family_id: UUID | None = None,
    ) -> tuple[str, datetime]:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        payload: dict[str, object] = {
            "sub": str(user_id),
            "jti": str(token_id),
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            TOKEN_TYPE_CLAIM: token_type,
        }
        if family_id is not None:
            payload[FAMILY_CLAIM] = str(family_id)
        return jwt.encode(payload, self._secret, algorithm=JWT_ALGORITHM), expires_at
