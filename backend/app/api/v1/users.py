"""Current user, sessions, export and account deletion."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Response, status
from fastapi.responses import JSONResponse

from app.auth.account_service import AccountService
from app.auth.dependencies import CurrentUser, get_account_service, get_auth_service, get_app_settings
from app.auth.schemas import (
    ConsentState,
    CurrentUserResponse,
    DeleteAccountRequest,
    ListSessionsRequest,
    SessionOut,
)
from app.auth.service import AuthService
from app.core.config import Settings
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(
    current_user: CurrentUser,
    entitlements: EntitlementsService = Depends(get_entitlements_service),
    settings: Settings = Depends(get_app_settings),
) -> CurrentUserResponse:
    await entitlements.ensure_free_subscription(current_user.id)
    tier = await entitlements.get_tier(current_user.id)
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        tier=tier,
        locale=current_user.locale,
        is_active=current_user.is_active,
        role=current_user.role,
        email_verified=current_user.email_verified_at is not None,
        email_verified_at=current_user.email_verified_at,
        accepted_terms_at=current_user.accepted_terms_at,
        terms_version=current_user.terms_version,
        privacy_version=current_user.privacy_version,
        consent=ConsentState(
            terms_version=current_user.terms_version,
            privacy_version=current_user.privacy_version,
            accepted_terms_at=current_user.accepted_terms_at,
            terms_url=settings.terms_url,
            privacy_url=settings.privacy_url,
        ),
        created_at=current_user.created_at,
    )


@router.post("/me/sessions", response_model=list[SessionOut])
async def list_sessions(
    payload: ListSessionsRequest,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SessionOut]:
    rows = await auth_service.list_sessions(
        current_user, current_refresh_token=payload.current_refresh_token
    )
    return [SessionOut.model_validate(row, from_attributes=True) for row in rows]


@router.get("/me/sessions", response_model=list[SessionOut])
async def list_sessions_get(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SessionOut]:
    rows = await auth_service.list_sessions(current_user, current_refresh_token=None)
    return [SessionOut.model_validate(row, from_attributes=True) for row in rows]


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.revoke_session(current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    current_user: CurrentUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.revoke_all_sessions(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/export")
async def export_my_data(
    current_user: CurrentUser,
    account_service: AccountService = Depends(get_account_service),
) -> JSONResponse:
    payload = await account_service.export_user_data(current_user)
    if not isinstance(payload, dict) or "exported_at" not in payload:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "export_failed",
                    "message": "Экспорт не сформирован.",
                }
            },
        )
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="foodai-export.json"',
        },
    )


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account_post(
    payload: DeleteAccountRequest,
    current_user: CurrentUser,
    account_service: AccountService = Depends(get_account_service),
) -> Response:
    """Preferred delete path — JSON body is reliable across HTTP clients/proxies."""
    await account_service.delete_account(
        current_user, confirmation=payload.confirmation
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: CurrentUser,
    account_service: AccountService = Depends(get_account_service),
    payload: Annotated[DeleteAccountRequest | None, Body()] = None,
    x_confirm_delete: Annotated[str | None, Header(alias="X-Confirm-Delete")] = None,
) -> Response:
    """Legacy DELETE. Prefer POST /users/me/delete when clients drop DELETE bodies."""
    confirmation = (
        payload.confirmation
        if payload is not None
        else (x_confirm_delete or "")
    )
    await account_service.delete_account(current_user, confirmation=confirmation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
