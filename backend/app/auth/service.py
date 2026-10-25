"""AuthService: registration, login, refresh, verification, reset and sessions."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import (
    AccountDisabled,
    InvalidCredentials,
    InvalidToken,
    TokenExpired,
    TokenAlreadyUsed,
)
from app.auth.models import RefreshToken, User
from app.auth.passwords import PasswordHasher
from app.auth.repository import AuthRepository
from app.auth.tokens import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TokenService
from app.core.config import Settings
from app.core.errors import ApiError, OwnershipDenied
from app.core.models import as_utc, utcnow
from app.core.rate_limit import RateLimiter
from app.email.provider import EmailProvider, OutboundEmail

logger = logging.getLogger(__name__)

DEFAULT_TIER = "free"
GENERIC_AUTH_MESSAGE = "Если аккаунт существует, мы отправили письмо с инструкциями."


class ForbiddenAdmin(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="admin_required",
            message="Требуются права администратора.",
        )


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


@dataclass(frozen=True)
class SessionView:
    id: UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    device_label: str | None
    platform: str | None
    app_version: str | None
    is_current: bool


_LOGIN_EMAIL_LIMIT = 10
_LOGIN_IP_LIMIT = 30
_LOGIN_WINDOW_SECONDS = 900
_REGISTER_IP_LIMIT = 10
_REGISTER_WINDOW_SECONDS = 3600


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: AuthRepository,
        passwords: PasswordHasher,
        tokens: TokenService,
        settings: Settings,
        email: EmailProvider,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._passwords = passwords
        self._tokens = tokens
        self._settings = settings
        self._email = email
        self._rate_limiter = rate_limiter

    async def register(
        self,
        *,
        email: str,
        password: str,
        locale: str,
        accepted_terms_at: datetime | None,
        platform: str | None = None,
        app_version: str | None = None,
        device_label: str | None = None,
        client_key: str | None = None,
    ) -> TokenPair:
        if client_key:
            await self._rate(
                f"register_ip:{client_key}",
                limit=_REGISTER_IP_LIMIT,
                window_seconds=_REGISTER_WINDOW_SECONDS,
            )
        role = "admin" if email.strip().lower() in self._settings.admin_email_set() else "user"
        user = await self._repository.create_user(
            email=email,
            password_hash=self._passwords.hash(password),
            locale=locale,
            accepted_terms_at=accepted_terms_at,
            terms_version=self._settings.terms_version,
            privacy_version=self._settings.privacy_version,
            role=role,
        )
        pair = await self._issue_pair(
            user,
            platform=platform,
            app_version=app_version,
            device_label=device_label,
        )
        await self._issue_verification_email(user)
        await self._session.commit()
        logger.info("user_registered", extra={"user_id": str(user.id)})
        return pair

    async def login(
        self,
        *,
        email: str,
        password: str,
        platform: str | None = None,
        app_version: str | None = None,
        device_label: str | None = None,
        client_key: str | None = None,
    ) -> TokenPair:
        email_key = (email or "").strip().lower()
        if client_key:
            await self._rate(
                f"login_ip:{client_key}",
                limit=_LOGIN_IP_LIMIT,
                window_seconds=_LOGIN_WINDOW_SECONDS,
            )
        await self._rate(
            f"login_email:{email_key}",
            limit=_LOGIN_EMAIL_LIMIT,
            window_seconds=_LOGIN_WINDOW_SECONDS,
        )
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
        self._maybe_promote_admin(user)
        pair = await self._issue_pair(
            user,
            platform=platform,
            app_version=app_version,
            device_label=device_label,
        )
        await self._session.commit()
        logger.info("user_logged_in", extra={"user_id": str(user.id)})
        return pair

    async def rotate(self, refresh_token: str) -> TokenPair:
        claims = self._tokens.decode(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        stored = await self._repository.get_refresh_token_by_hash(
            self._tokens.hash_token(refresh_token), for_update=True
        )
        if stored is None or stored.user_id != claims.user_id:
            raise InvalidToken()

        now = utcnow()
        if stored.is_revoked:
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
            user,
            family_id=stored.family_id,
            platform=stored.platform,
            app_version=stored.app_version,
            device_label=stored.device_label,
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
            self._tokens.hash_token(refresh_token), for_update=True
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

    async def resend_verification(self, *, email: str, client_key: str) -> dict[str, str]:
        await self._rate(f"verify_resend:{client_key}", limit=3, window_seconds=3600)
        user = await self._repository.get_user_by_email(email)
        if user is not None and user.email_verified_at is None:
            await self._issue_verification_email(user)
            await self._session.commit()
        return {"message": GENERIC_AUTH_MESSAGE}

    async def verify_email(self, *, token: str) -> dict[str, str]:
        digest = self._tokens.hash_token(token)
        row = await self._repository.get_email_verification_by_hash(digest)
        if row is None:
            raise InvalidToken()
        now = utcnow()
        if row.used_at is not None:
            raise TokenAlreadyUsed()
        if as_utc(row.expires_at) <= now:
            raise TokenExpired()
        user = await self._repository.get_user(row.user_id)
        if user is None:
            raise InvalidToken()
        user.email_verified_at = now
        row.used_at = now
        await self._repository.invalidate_unused_email_tokens(user.id, at=now)
        await self._session.commit()
        logger.info("email_verified", extra={"user_id": str(user.id)})
        return {"message": "Email подтверждён."}

    async def forgot_password(self, *, email: str, client_key: str) -> dict[str, str]:
        await self._rate(f"forgot:{client_key}", limit=5, window_seconds=3600)
        await self._rate(f"forgot_email:{email.strip().lower()}", limit=3, window_seconds=3600)
        user = await self._repository.get_user_by_email(email)
        if user is not None and user.is_active:
            raw = secrets.token_urlsafe(32)
            expires = utcnow() + timedelta(hours=self._settings.password_reset_ttl_hours)
            await self._repository.invalidate_unused_password_tokens(user.id, at=utcnow())
            await self._repository.add_password_reset_token(
                user_id=user.id,
                token_hash=self._tokens.hash_token(raw),
                expires_at=expires,
            )
            await self._email.send(
                OutboundEmail(
                    to_email=user.email,
                    subject="Сброс пароля FoodAI",
                    body_text=(
                        "Чтобы сбросить пароль, используйте одноразовый токен в приложении.\n"
                        f"Срок действия: {self._settings.password_reset_ttl_hours} ч."
                    ),
                    debug_token=raw if self._settings.app_env == "test" else None,
                )
            )
            await self._session.commit()
            logger.info("password_reset_requested", extra={"user_id": str(user.id)})
        return {"message": GENERIC_AUTH_MESSAGE}

    async def reset_password(self, *, token: str, new_password: str) -> dict[str, str]:
        digest = self._tokens.hash_token(token)
        row = await self._repository.get_password_reset_by_hash(digest)
        if row is None:
            raise InvalidToken()
        now = utcnow()
        if row.used_at is not None:
            raise TokenAlreadyUsed()
        if as_utc(row.expires_at) <= now:
            raise TokenExpired()
        user = await self._repository.get_user(row.user_id)
        if user is None or not user.is_active:
            raise InvalidToken()
        await self._repository.update_password_hash(user, self._passwords.hash(new_password))
        row.used_at = now
        await self._repository.invalidate_unused_password_tokens(user.id, at=now)
        await self._repository.revoke_all_for_user(user.id, at=now)
        await self._session.commit()
        logger.info("password_reset_completed", extra={"user_id": str(user.id)})
        return {"message": "Пароль обновлён. Войдите снова."}

    async def list_sessions(
        self, user: User, *, current_refresh_token: str | None
    ) -> list[SessionView]:
        current_id: UUID | None = None
        if current_refresh_token:
            stored = await self._repository.get_refresh_token_by_hash(
                self._tokens.hash_token(current_refresh_token)
            )
            if stored is not None:
                current_id = stored.id
        rows = await self._repository.list_active_sessions(user.id)
        return [
            SessionView(
                id=row.id,
                created_at=row.created_at,
                last_used_at=row.last_used_at,
                expires_at=row.expires_at,
                device_label=row.device_label,
                platform=row.platform,
                app_version=row.app_version,
                is_current=row.id == current_id,
            )
            for row in rows
        ]

    async def revoke_session(self, user: User, session_id: UUID) -> None:
        row = await self._repository.get_refresh_token(session_id)
        if row is None or row.user_id != user.id:
            raise OwnershipDenied()
        if not row.is_revoked:
            await self._repository.revoke_refresh_token(row, at=utcnow())
            await self._session.commit()

    async def revoke_all_sessions(self, user: User) -> int:
        count = await self._repository.revoke_all_for_user(user.id, at=utcnow())
        await self._session.commit()
        return count

    def require_admin(self, user: User) -> None:
        if user.role != "admin":
            raise ForbiddenAdmin()

    async def _issue_verification_email(self, user: User) -> None:
        raw = secrets.token_urlsafe(32)
        expires = utcnow() + timedelta(hours=self._settings.email_verification_ttl_hours)
        await self._repository.invalidate_unused_email_tokens(user.id, at=utcnow())
        await self._repository.add_email_verification_token(
            user_id=user.id,
            token_hash=self._tokens.hash_token(raw),
            expires_at=expires,
        )
        await self._email.send(
            OutboundEmail(
                to_email=user.email,
                subject="Подтверждение email FoodAI",
                body_text="Подтвердите email одноразовым токеном в приложении.",
                debug_token=raw if self._settings.app_env == "test" else None,
            )
        )

    def _maybe_promote_admin(self, user: User) -> None:
        if user.email.lower() in self._settings.admin_email_set() and user.role != "admin":
            user.role = "admin"

    async def _rate(self, key: str, *, limit: int, window_seconds: int) -> None:
        if self._rate_limiter is None:
            return
        await self._rate_limiter.hit(key, limit=limit, window_seconds=window_seconds)

    async def _issue_pair(
        self,
        user: User,
        *,
        family_id: UUID | None = None,
        platform: str | None = None,
        app_version: str | None = None,
        device_label: str | None = None,
    ) -> TokenPair:
        pair, _ = await self._issue_pair_with_id(
            user,
            family_id=family_id,
            platform=platform,
            app_version=app_version,
            device_label=device_label,
        )
        return pair

    async def _issue_pair_with_id(
        self,
        user: User,
        *,
        family_id: UUID | None = None,
        platform: str | None = None,
        app_version: str | None = None,
        device_label: str | None = None,
    ) -> tuple[TokenPair, UUID]:
        access = self._tokens.create_access_token(user.id)
        refresh = self._tokens.create_refresh_token(user.id, family_id=family_id)
        await self._repository.add_refresh_token(
            token_id=refresh.token_id,
            user_id=user.id,
            token_hash=self._tokens.hash_token(refresh.token),
            family_id=refresh.family_id,
            expires_at=refresh.expires_at,
            platform=platform,
            app_version=app_version,
            device_label=device_label,
            last_used_at=utcnow(),
        )
        pair = TokenPair(
            access_token=access.token,
            refresh_token=refresh.token,
            expires_in=access.expires_in,
            user=user,
        )
        return pair, refresh.token_id
