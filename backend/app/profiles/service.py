"""ProfileService: onboarding data, goals, preferences, restrictions and pantry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.nutrition.engine import GoalRequest, NutritionEngine, NutritionTargets
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from app.profiles.normalization import normalize_food_name, normalize_unique
from app.profiles.repository import ProfileRepository
from app.profiles.schemas import ProfileUpdateRequest, TargetPreviewRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileSnapshot:
    profile: UserProfile
    goal: Goal | None
    preferences: list[FoodPreference]
    restrictions: list[FoodRestriction]
    pantry: list[AvailableProduct]


def goal_request(payload: TargetPreviewRequest) -> GoalRequest:
    return GoalRequest(
        sex=payload.sex,
        age_years=payload.age_years,
        height_cm=payload.height_cm,
        current_weight_kg=payload.current_weight_kg,
        activity_level=payload.activity_level,
        goal_type=payload.goal_type,
        target_weight_kg=payload.target_weight_kg,
        desired_weekly_change_kg=payload.desired_weekly_change_kg,
        daily_calorie_mode=payload.daily_calorie_mode,
        daily_calorie_value=payload.daily_calorie_value,
    )


class ProfileService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: ProfileRepository,
        nutrition: NutritionEngine,
    ) -> None:
        self._session = session
        self._repository = repository
        self._nutrition = nutrition

    def preview_targets(self, payload: TargetPreviewRequest) -> NutritionTargets:
        return self._nutrition.calculate(goal_request(payload))

    async def ensure_profile(self, user_id: UUID) -> UserProfile:
        """Idempotent: registration and both profile endpoints rely on it."""
        profile = await self._repository.get_profile(user_id)
        if profile is None:
            profile = await self._repository.create_profile(user_id)
            await self._session.commit()
        return profile

    async def get_snapshot(self, user_id: UUID) -> ProfileSnapshot:
        profile = await self.ensure_profile(user_id)
        return ProfileSnapshot(
            profile=profile,
            goal=await self._repository.get_active_goal(user_id),
            preferences=await self._repository.list_preferences(user_id),
            restrictions=await self._repository.list_restrictions(user_id),
            pantry=await self._repository.list_pantry(user_id),
        )

    async def update(
        self, user_id: UUID, payload: ProfileUpdateRequest
    ) -> tuple[ProfileSnapshot, NutritionTargets]:
        # Targets are computed first: rejected goals must not write anything.
        targets = self._nutrition.calculate(goal_request(payload))

        profile = await self._repository.get_profile(user_id)
        if profile is None:
            profile = await self._repository.create_profile(user_id)

        profile.sex = payload.sex
        profile.age_years = payload.age_years
        profile.height_cm = payload.height_cm
        profile.current_weight_kg = payload.current_weight_kg
        profile.activity_level = payload.activity_level
        profile.meals_per_day = payload.meals_per_day
        profile.daily_calorie_mode = payload.daily_calorie_mode
        profile.daily_calorie_value = payload.daily_calorie_value
        profile.grocery_budget_weekly = payload.grocery_budget_weekly
        profile.currency = payload.currency
        profile.max_cook_time_minutes = payload.max_cook_time_minutes
        profile.household_size = payload.household_size
        profile.timezone = payload.timezone

        goal = await self._apply_goal(user_id, payload, targets)
        profile.active_goal_id = goal.id

        await self._repository.replace_preferences(
            user_id, self._build_preferences(user_id, payload)
        )
        await self._repository.replace_restrictions(
            user_id, self._build_restrictions(user_id, payload)
        )
        await self._repository.replace_pantry(
            user_id, self._build_pantry(user_id, payload)
        )
        await self._session.commit()
        logger.info("profile_updated", extra={"user_id": str(user_id)})

        return await self.get_snapshot(user_id), targets

    async def _apply_goal(
        self, user_id: UUID, payload: ProfileUpdateRequest, targets: NutritionTargets
    ) -> Goal:
        goal = await self._repository.get_active_goal(user_id)
        if goal is None:
            goal = Goal(
                user_id=user_id,
                goal_type=payload.goal_type,
                start_weight_kg=payload.current_weight_kg,
                started_at=datetime.now(UTC).date(),
                status="active",
                nutrition_policy_version=self._nutrition.policy_version,
            )
        # start_weight_kg keeps the weight the goal began with.
        goal.goal_type = payload.goal_type
        goal.target_weight_kg = payload.target_weight_kg
        goal.desired_weekly_change_kg = payload.desired_weekly_change_kg
        goal.calorie_target_kcal = targets.recommended_calorie_target_kcal
        goal.protein_target_g = Decimal(targets.macro_targets_g.protein_g)
        goal.fat_target_g = Decimal(targets.macro_targets_g.fat_g)
        goal.carbohydrate_target_g = Decimal(targets.macro_targets_g.carbohydrate_g)
        goal.bmr_kcal = targets.bmr_kcal
        goal.tdee_kcal = targets.tdee_kcal
        goal.safety_floor_kcal = targets.applied_safety_floor_kcal
        goal.nutrition_policy_version = self._nutrition.policy_version
        return await self._repository.add_goal(goal)

    @staticmethod
    def _build_preferences(
        user_id: UUID, payload: ProfileUpdateRequest
    ) -> list[FoodPreference]:
        preferences: list[FoodPreference] = []
        for names, preference_type in (
            (payload.liked_foods, "liked"),
            (payload.disliked_foods, "disliked"),
        ):
            preferences.extend(
                FoodPreference(
                    user_id=user_id,
                    normalized_food_name=name.normalized,
                    display_name=name.display,
                    preference_type=preference_type,
                )
                for name in normalize_unique(names)
            )
        return preferences

    @staticmethod
    def _build_restrictions(
        user_id: UUID, payload: ProfileUpdateRequest
    ) -> list[FoodRestriction]:
        restrictions: list[FoodRestriction] = []
        for names, restriction_type in (
            (payload.excluded_foods, "excluded"),
            (payload.allergies, "allergy"),
        ):
            restrictions.extend(
                FoodRestriction(
                    user_id=user_id,
                    normalized_food_name=name.normalized,
                    display_name=name.display,
                    restriction_type=restriction_type,
                )
                for name in normalize_unique(names)
            )
        return restrictions

    @staticmethod
    def _build_pantry(
        user_id: UUID, payload: ProfileUpdateRequest
    ) -> list[AvailableProduct]:
        merged: dict[tuple[str, str], AvailableProduct] = {}
        for item in payload.available_products:
            normalized = normalize_food_name(item.name)
            if not normalized:
                continue
            key = (normalized, item.unit)
            existing = merged.get(key)
            if existing is not None:
                existing.quantity_value += item.quantity
                existing.expires_on = existing.expires_on or item.expires_on
                continue
            merged[key] = AvailableProduct(
                user_id=user_id,
                display_name=item.name.strip(),
                normalized_name=normalized,
                quantity_value=item.quantity,
                unit=item.unit,
                expires_on=item.expires_on,
            )
        return list(merged.values())
