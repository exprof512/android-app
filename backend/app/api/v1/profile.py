"""Profile questionnaire and nutrition target endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.nutrition.engine import DISCLAIMER, NutritionTargets
from app.profiles.dependencies import get_profile_service
from app.profiles.models import Goal
from app.profiles.schemas import (
    GoalView,
    MacroTargets,
    PantryItemResponse,
    Preferences,
    ProfileFields,
    ProfileResponse,
    ProfileUpdateRequest,
    Restrictions,
    TargetPreviewRequest,
    TargetPreviewResponse,
)
from app.profiles.service import ProfileService, ProfileSnapshot

router = APIRouter(prefix="/profile", tags=["profile"])


def _goal_view(goal: Goal) -> GoalView:
    return GoalView(
        id=goal.id,
        goal_type=goal.goal_type,
        status=goal.status,
        start_weight_kg=goal.start_weight_kg,
        target_weight_kg=goal.target_weight_kg,
        desired_weekly_change_kg=goal.desired_weekly_change_kg,
        calorie_target_kcal=goal.calorie_target_kcal,
        macro_targets_g=MacroTargets(
            protein=int(goal.protein_target_g),
            fat=int(goal.fat_target_g),
            carbohydrate=int(goal.carbohydrate_target_g),
        ),
        bmr_kcal=goal.bmr_kcal,
        tdee_kcal=goal.tdee_kcal,
        safety_floor_kcal=goal.safety_floor_kcal,
        started_at=goal.started_at,
    )


def _profile_response(snapshot: ProfileSnapshot) -> ProfileResponse:
    def names(items: list, attribute: str, value: str) -> list[str]:
        return [
            item.display_name for item in items if getattr(item, attribute) == value
        ]

    return ProfileResponse(
        profile=ProfileFields.model_validate(snapshot.profile, from_attributes=True),
        goal=_goal_view(snapshot.goal) if snapshot.goal else None,
        preferences=Preferences(
            liked_foods=names(snapshot.preferences, "preference_type", "liked"),
            disliked_foods=names(snapshot.preferences, "preference_type", "disliked"),
        ),
        restrictions=Restrictions(
            excluded_foods=names(snapshot.restrictions, "restriction_type", "excluded"),
            allergies=names(snapshot.restrictions, "restriction_type", "allergy"),
        ),
        available_products=[
            PantryItemResponse(
                name=product.display_name,
                quantity=product.quantity_value,
                unit=product.unit,
                expires_on=product.expires_on,
            )
            for product in snapshot.pantry
        ],
        # The disclaimer travels with every calculated target.
        warnings=[DISCLAIMER] if snapshot.goal else [],
    )


def _target_response(targets: NutritionTargets) -> TargetPreviewResponse:
    return TargetPreviewResponse(
        bmr_kcal=targets.bmr_kcal,
        tdee_kcal=targets.tdee_kcal,
        recommended_calorie_target_kcal=targets.recommended_calorie_target_kcal,
        applied_safety_floor_kcal=targets.applied_safety_floor_kcal,
        macro_targets_g=MacroTargets(
            protein=targets.macro_targets_g.protein_g,
            fat=targets.macro_targets_g.fat_g,
            carbohydrate=targets.macro_targets_g.carbohydrate_g,
        ),
        warnings=targets.warnings,
    )


@router.get("", response_model=ProfileResponse)
async def read_profile(
    current_user: CurrentUser,
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    snapshot = await profile_service.get_snapshot(current_user.id)
    return _profile_response(snapshot)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser,
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    snapshot, targets = await profile_service.update(current_user.id, payload)
    response = _profile_response(snapshot)
    response.warnings = targets.warnings
    return response


@router.post("/calculate-target", response_model=TargetPreviewResponse)
async def calculate_target(
    payload: TargetPreviewRequest,
    current_user: CurrentUser,
    profile_service: ProfileService = Depends(get_profile_service),
) -> TargetPreviewResponse:
    return _target_response(profile_service.preview_targets(payload))
