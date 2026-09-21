"""AuthService: registration, login, refresh rotation and logout."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AccountDisabled, InvalidCredentials, InvalidToken
from app.auth.models import User
from app.auth.passwords import PasswordHasher
from app.auth.repository import AuthRepository
from app.auth.tokens import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenService
from app.core.errors import OwnershipDenied
from app.core.models import utcnow

logger = logging.getLogger(__name__)

# Phase 2 has no subscriptions table yet; EntitlementsService replaces this later.
DEFAULT_TIER = "free"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: AuthRepository,
        passwords: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._session = session
        self._repository = repository
        self._passwords = passwords
        self._tokens = tokens

    async def register(
        self,
        *,
        email: str,
        password: str,
        locale: str,
        accepted_terms_at: datetime | None,
    ) -> TokenPair:
        user = await self._repository.create_user(
            email=email,
            password_hash=self._passwords.hash(password),
            locale=locale,
            accepted_terms_at=accepted_terms_at,
        )
        pair = await self._issue_pair(user)
        await self._session.commit()
        logger.info("user_registered", extra={"user_id": str(user.id)})
        return pair

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._repository.get_user_by_email(email)
        if user is None:
            self._passwords.spend_verification_time()
            raise InvalidCredentials()
        if not self._passwords.verify(password, user.password_hash):
            raise InvalidCredentials()
        if not user.is_active:
            raise AccountDisabled()
        if self._passwords.needs_rehash(user.password_hash):
            await self._repository.update_password_hash(
                user, self._passwords.hash(password)
            )
        pair = await self._issue_pair(user)
        await self._session.commit()
        logger.info("user_logged_in", extra={"user_id": str(user.id)})
        return pair

    async def rotate(self, refresh_token: str) -> TokenPair:
        claims = self._tokens.decode(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        stored = await self._repository.get_refresh_token_by_hash(
            self._tokens.hash_token(refresh_token)
        )
        if stored is None or stored.user_id != claims.user_id:
            raise InvalidToken()

        now = utcnow()
        if stored.is_revoked:
            # A revoked token presented again means the value leaked: drop the family.
            await self._repository.revoke_family(stored.family_id, at=now)
            await self._session.commit()
            logger.warning(
                "refresh_token_reuse_detected",
                extra={"user_id": str(stored.user_id), "error_code": "invalid_token"},
            )
            raise InvalidToken()
        if stored.is_expired(now):
            await self._repository.revoke_refresh_token(stored, at=now)
            await self._session.commit()
            raise InvalidToken()

        user = await self._repository.get_user(stored.user_id)
        if user is None:
            raise InvalidToken()
        if not user.is_active:
            raise AccountDisabled()

        pair, issued_token_id = await self._issue_pair_with_id(
            user, family_id=stored.family_id
        )
        await self._repository.revoke_refresh_token(
            stored, at=now, replaced_by_id=issued_token_id
        )
        await self._session.commit()
        logger.info("refresh_token_rotated", extra={"user_id": str(user.id)})
        return pair

    async def logout(self, *, refresh_token: str, user: User) -> None:
        claims = self._tokens.decode(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        if claims.user_id != user.id:
            raise OwnershipDenied()

        stored = await self._repository.get_refresh_token_by_hash(
            self._tokens.hash_token(refresh_token)
        )
        if stored is None:
            return
        if stored.user_id != user.id:
            raise OwnershipDenied()
        if not stored.is_revoked:
            await self._repository.revoke_refresh_token(stored, at=utcnow())
            await self._session.commit()
        logger.info("user_logged_out", extra={"user_id": str(user.id)})

    async def authenticate(self, access_token: str) -> User:
        claims = self._tokens.decode(access_token, expected_type=ACCESS_TOKEN_TYPE)
        user = await self._repository.get_user(claims.user_id)
        if user is None:
            raise InvalidToken()
        if not user.is_active:
            raise AccountDisabled()
        return user

    async def _issue_pair(self, user: User, *, family_id: UUID | None = None) -> TokenPair:
        pair, _ = await self._issue_pair_with_id(user, family_id=family_id)
        return pair

    async def _issue_pair_with_id(
        self, user: User, *, family_id: UUID | None = None
    ) -> tuple[TokenPair, UUID]:
        access = self._tokens.create_access_token(user.id)
        refresh = self._tokens.create_refresh_token(user.id, family_id=family_id)
        await self._repository.add_refresh_token(
            token_id=refresh.token_id,
            user_id=user.id,
            token_hash=self._tokens.hash_token(refresh.token),
            family_id=refresh.family_id,
            expires_at=refresh.expires_at,
        )
        pair = TokenPair(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=access.expires_in,
            user=user,
        )
        return pair, refresh.token_id
