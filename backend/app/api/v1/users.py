"""Current user endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.auth.schemas import CurrentUserResponse
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(
    current_user: CurrentUser,
    entitlements: EntitlementsService = Depends(get_entitlements_service),
) -> CurrentUserResponse:
    await entitlements.ensure_free_subscription(current_user.id)
    tier = await entitlements.get_tier(current_user.id)
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        tier=tier,
        locale=current_user.locale,
        is_active=current_user.is_active,
        accepted_terms_at=current_user.accepted_terms_at,
        created_at=current_user.created_at,
    )
