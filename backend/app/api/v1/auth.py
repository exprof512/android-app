"""Registration, login, refresh, verification and password reset endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.dependencies import CurrentUser, get_auth_service, get_app_settings, get_email_provider
from app.auth.schemas import (
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenPairResponse,
    UserSummary,
    VerifyEmailRequest,
)
from app.auth.service import AuthService, TokenPair
from app.core.config import Settings
from app.email.provider import MockEmailProvider
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService
from app.profiles.dependencies import get_profile_service
from app.profiles.service import ProfileService

router = APIRouter(prefix="/auth", tags=["auth"])


async def _token_pair_response(
    pair: TokenPair, entitlements: EntitlementsService
) -> TokenPairResponse:
    await entitlements.ensure_free_subscription(pair.user.id)
    tier = await entitlements.get_tier(pair.user.id)
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
        user=UserSummary(id=pair.user.id, email=pair.user.email, tier=tier),
    )


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    profile_service: ProfileService = Depends(get_profile_service),
    entitlements: EntitlementsService = Depends(get_entitlements_service),
) -> TokenPairResponse:
    pair = await auth_service.register(
        email=payload.email,
        password=payload.password,
        locale=payload.locale,
        accepted_terms_at=payload.accepted_terms_at,
        platform=payload.platform,
        app_version=payload.app_version,
        device_label=payload.device_label,
    )
    await profile_service.ensure_profile(pair.user.id)
    return await _token_pair_response(pair, entitlements)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    entitlements: EntitlementsService = Depends(get_entitlements_service),
) -> TokenPairResponse:
    pair = await auth_service.login(
        email=payload.email,
        password=payload.password,
        platform=payload.platform,
        app_version=payload.app_version,
        device_label=payload.device_label,
    )
    return await _token_pair_response(pair, entitlements)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
    entitlements: EntitlementsService = Depends(get_entitlements_service),
) -> TokenPairResponse:
    pair = await auth_service.rotate(payload.refresh_token)
    return await _token_pair_response(pair, entitlements)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.logout(refresh_token=payload.refresh_token, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", response_model=GenericMessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> GenericMessageResponse:
    result = await auth_service.verify_email(token=payload.token)
    return GenericMessageResponse(**result)


@router.post("/resend-verification", response_model=GenericMessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> GenericMessageResponse:
    result = await auth_service.resend_verification(
        email=payload.email, client_key=_client_key(request)
    )
    return GenericMessageResponse(**result)


@router.post("/forgot-password", response_model=GenericMessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> GenericMessageResponse:
    result = await auth_service.forgot_password(
        email=payload.email, client_key=_client_key(request)
    )
    return GenericMessageResponse(**result)


@router.post("/reset-password", response_model=GenericMessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> GenericMessageResponse:
    result = await auth_service.reset_password(
        token=payload.token, new_password=payload.new_password
    )
    return GenericMessageResponse(**result)


@router.get("/_test/last-email")
async def test_last_email(
    email: str,
    provider: MockEmailProvider = Depends(get_email_provider),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str | None]:
    """Test-only peek at MockEmailProvider debug tokens. Disabled outside test."""
    if settings.app_env != "test":
        from app.core.errors import ApiError

        raise ApiError(status_code=404, code="not_found", message="Not found")
    message = provider.last_for(email)
    return {
        "to_email": message.to_email if message else None,
        "subject": message.subject if message else None,
        "debug_token": message.debug_token if message else None,
    }
