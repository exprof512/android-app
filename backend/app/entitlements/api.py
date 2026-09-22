"""Entitlement status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.dependencies import CurrentUser
from app.entitlements import constants
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService

router = APIRouter(prefix="/entitlements", tags=["entitlements"])


class FeatureUsageOut(BaseModel):
    feature: str
    limit_value: int | None = None
    used_value: int = 0
    remaining: int | None = None


class EntitlementStatusOut(BaseModel):
    tier: str
    features: list[FeatureUsageOut] = Field(default_factory=list)
    premium_only: list[str] = Field(
        default_factory=lambda: list(constants.PREMIUM_ONLY_FEATURES)
    )


@router.get("/me", response_model=EntitlementStatusOut)
async def read_entitlements(
    user: CurrentUser,
    service: EntitlementsService = Depends(get_entitlements_service),
) -> EntitlementStatusOut:
    await service.ensure_free_subscription(user.id)
    tier = await service.get_tier(user.id)
    features = []
    for feature in (
        constants.FEATURE_MEAL_PLAN_GENERATE,
        constants.FEATURE_MEAL_REPLACE,
        constants.FEATURE_CHAT_MESSAGE,
        constants.FEATURE_IMAGE_REGENERATE,
    ):
        status = await service.usage_status(user.id, feature)
        features.append(
            FeatureUsageOut(
                feature=status.feature,
                limit_value=status.limit_value,
                used_value=status.used_value,
                remaining=status.remaining,
            )
        )
    return EntitlementStatusOut(tier=tier, features=features)
