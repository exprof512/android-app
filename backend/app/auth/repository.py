"""Persistence for users and refresh tokens."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import EmailAlreadyRegistered
from app.auth.models import RefreshToken, User


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        locale: str,
        accepted_terms_at: datetime | None,
    ) -> User:
        user = User(
            email=normalize_email(email),
            password_hash=password_hash,
            locale=locale,
            accepted_terms_at=accepted_terms_at,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()
            raise EmailAlreadyRegistered() from error
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == normalize_email(email))
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._session.flush()

    async def add_refresh_token(
        self,
        *,
        token_id: UUID,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            id=token_id,
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self._session.add(refresh_token)
        await self._session.flush()
        return refresh_token

    async def get_refresh_token_by_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        if for_update:
            # Serializes concurrent rotations of the same token.
            statement = statement.with_for_update()
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def revoke_refresh_token(
        self, refresh_token: RefreshToken, *, at: datetime, replaced_by_id: UUID | None = None
    ) -> None:
        refresh_token.revoked_at = at
        refresh_token.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        await self._session.execute(statement)
        await self._session.flush()
