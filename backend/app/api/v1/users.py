"""Current user endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.auth.schemas import CurrentUserResponse
from app.auth.service import DEFAULT_TIER

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        tier=DEFAULT_TIER,
        locale=current_user.locale,
        is_active=current_user.is_active,
        accepted_terms_at=current_user.accepted_terms_at,
        created_at=current_user.created_at,
    )
