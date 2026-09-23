"""Auth dependency wiring and the authenticated-user dependency."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.account_service import AccountService
from app.auth.errors import InvalidToken
from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.service import AuthService, ForbiddenAdmin
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session, get_services
from app.core.rate_limit import MemoryRateLimiter
from app.core.services import Services
from app.email.provider import MockEmailProvider

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="AccessToken")


def get_email_provider(services: Services = Depends(get_services)) -> MockEmailProvider:
    if services.email_provider is None:
        services.email_provider = MockEmailProvider()
    return services.email_provider  # type: ignore[return-value]


def get_rate_limiter(services: Services = Depends(get_services)):
    if services.rate_limiter is None:
        services.rate_limiter = MemoryRateLimiter()
    return services.rate_limiter


def get_app_settings(services: Services = Depends(get_services)) -> Settings:
    return services.settings or get_settings()


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
    email=Depends(get_email_provider),
    rate_limiter=Depends(get_rate_limiter),
    settings: Settings = Depends(get_app_settings),
) -> AuthService:
    return AuthService(
        session=session,
        repository=AuthRepository(session),
        passwords=services.passwords,
        tokens=services.tokens,
        settings=settings,
        email=email,
        rate_limiter=rate_limiter,
    )


def get_account_service(
    session: AsyncSession = Depends(get_db_session),
) -> AccountService:
    return AccountService(session=session, auth_repository=AuthRepository(session))


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidToken()
    user = await auth_service.authenticate(credentials.credentials)
    request.state.user_id = str(user.id)
    return user


async def get_admin_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise ForbiddenAdmin()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
