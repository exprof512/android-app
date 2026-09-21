"""Auth dependency wiring and the authenticated-user dependency."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import InvalidToken
from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.service import AuthService
from app.core.dependencies import get_db_session, get_services
from app.core.services import Services

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="AccessToken")


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
) -> AuthService:
    return AuthService(
        session=session,
        repository=AuthRepository(session),
        passwords=services.passwords,
        tokens=services.tokens,
    )


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


CurrentUser = Annotated[User, Depends(get_current_user)]
