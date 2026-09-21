"""Registration, login, refresh rotation and logout endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.dependencies import CurrentUser, get_auth_service
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserSummary,
)
from app.auth.service import DEFAULT_TIER, AuthService, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair_response(pair: TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=UserSummary(id=pair.user.id, email=pair.user.email, tier=DEFAULT_TIER),
    )


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPairResponse:
    pair = await auth_service.register(
        email=payload.email,
        password=payload.password,
        locale=payload.locale,
        accepted_terms_at=payload.accepted_terms_at,
    )
    return _token_pair_response(pair)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPairResponse:
    pair = await auth_service.login(email=payload.email, password=payload.password)
    return _token_pair_response(pair)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPairResponse:
    pair = await auth_service.rotate(payload.refresh_token)
    return _token_pair_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.logout(refresh_token=payload.refresh_token, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
