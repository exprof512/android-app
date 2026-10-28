"""Account deletion and GDPR-style data export."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.chat.models import AiConversation, AiMessage
from app.core.errors import ApiError
from app.core.models import utcnow
from app.entitlements.models import Subscription, UsageLimit
from app.meal_plans.models import MealPlan, MealPlanItem
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from app.progress.models import WeightEntry
from app.meal_plans.models import MealPlan, MealPlanItem
from app.recipes.models import Recipe, UserRecipeFavorite
from app.shopping.models import ShoppingList, ShoppingListItem

logger = logging.getLogger(__name__)


class DeleteConfirmationRequired(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="delete_confirmation_required",
            message="Для удаления аккаунта отправьте confirmation=DELETE.",
        )


def _dec(value: Decimal | int | float | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


class AccountService:
    def __init__(self, *, session: AsyncSession, auth_repository: AuthRepository) -> None:
        self._session = session
        self._auth = auth_repository

    async def export_user_data(self, user: User) -> dict[str, Any]:
        profile = (
            await self._session.execute(
                select(UserProfile).where(UserProfile.user_id == user.id)
            )
        ).scalar_one_or_none()
        goals = list(
            (await self._session.execute(select(Goal).where(Goal.user_id == user.id)))
            .scalars()
        )
        prefs = list(
            (
                await self._session.execute(
                    select(FoodPreference).where(FoodPreference.user_id == user.id)
                )
            ).scalars()
        )
        restrictions = list(
            (
                await self._session.execute(
                    select(FoodRestriction).where(FoodRestriction.user_id == user.id)
                )
            ).scalars()
        )
        pantry = list(
            (
                await self._session.execute(
                    select(AvailableProduct).where(AvailableProduct.user_id == user.id)
                )
            ).scalars()
        )
        weights = list(
            (
                await self._session.execute(
                    select(WeightEntry).where(WeightEntry.user_id == user.id)
                )
            ).scalars()
        )
        plans = list(
            (
                await self._session.execute(
                    select(MealPlan).where(MealPlan.user_id == user.id)
                )
            ).scalars()
        )
        plan_ids = [p.id for p in plans]
        items: list[MealPlanItem] = []
        if plan_ids:
            items = list(
                (
                    await self._session.execute(
                        select(MealPlanItem).where(MealPlanItem.meal_plan_id.in_(plan_ids))
                    )
                ).scalars()
            )
        shopping = list(
            (
                await self._session.execute(
                    select(ShoppingList).where(ShoppingList.user_id == user.id)
                )
            ).scalars()
        )
        shopping_ids = [s.id for s in shopping]
        shopping_items: list[ShoppingListItem] = []
        if shopping_ids:
            shopping_items = list(
                (
                    await self._session.execute(
                        select(ShoppingListItem).where(
                            ShoppingListItem.shopping_list_id.in_(shopping_ids)
                        )
                    )
                ).scalars()
            )
        conversations = list(
            (
                await self._session.execute(
                    select(AiConversation).where(AiConversation.user_id == user.id)
                )
            ).scalars()
        )
        conv_ids = [c.id for c in conversations]
        messages: list[AiMessage] = []
        if conv_ids:
            messages = list(
                (
                    await self._session.execute(
                        select(AiMessage).where(AiMessage.conversation_id.in_(conv_ids))
                    )
                ).scalars()
            )
        favorites = list(
            (
                await self._session.execute(
                    select(UserRecipeFavorite).where(UserRecipeFavorite.user_id == user.id)
                )
            ).scalars()
        )

        # Optional nutrition logs if table exists in metadata
        warnings: list[str] = []
        nutrition_logs: list[dict[str, Any]] = []
        try:
            from app.nutrition.models import NutritionLog

            rows = list(
                (
                    await self._session.execute(
                        select(NutritionLog).where(NutritionLog.user_id == user.id)
                    )
                ).scalars()
            )
            nutrition_logs = [
                {
                    "id": str(r.id),
                    "logged_on": r.logged_on.isoformat(),
                    "meal_type": r.meal_type,
                    "description": r.description,
                    "calories_kcal": r.calories_kcal,
                    "protein_g": _dec(r.protein_g),
                    "fat_g": _dec(r.fat_g),
                    "carbohydrate_g": _dec(r.carbohydrate_g),
                    "servings": _dec(r.servings),
                    "source": r.source,
                    "recipe_id": str(r.recipe_id) if r.recipe_id else None,
                }
                for r in rows
            ]
        except Exception:
            nutrition_logs = []
            warnings.append("nutrition_logs_unavailable")

        water_entries: list[dict[str, Any]] = []
        try:
            from app.water.models import WaterEntry

            water_rows = list(
                (
                    await self._session.execute(
                        select(WaterEntry).where(WaterEntry.user_id == user.id)
                    )
                ).scalars()
            )
            water_entries = [
                {
                    "id": str(w.id),
                    "recorded_on": w.recorded_on.isoformat(),
                    "amount_ml": w.amount_ml,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
                for w in water_rows
            ]
        except Exception:
            water_entries = []
            warnings.append("water_entries_unavailable")

        return {
            "exported_at": utcnow().isoformat(),
            "warnings": warnings,
            "account": {
                "id": str(user.id),
                "email": user.email,
                "locale": user.locale,
                "role": user.role,
                "email_verified_at": user.email_verified_at.isoformat()
                if user.email_verified_at
                else None,
                "accepted_terms_at": user.accepted_terms_at.isoformat()
                if user.accepted_terms_at
                else None,
                "terms_version": user.terms_version,
                "privacy_version": user.privacy_version,
                "created_at": user.created_at.isoformat(),
            },
            "profile": None
            if profile is None
            else {
                "sex": profile.sex,
                "age_years": profile.age_years,
                "height_cm": _dec(profile.height_cm),
                "current_weight_kg": _dec(profile.current_weight_kg),
                "activity_level": profile.activity_level,
                "meals_per_day": profile.meals_per_day,
                "timezone": profile.timezone,
            },
            "goals": [
                {
                    "id": str(g.id),
                    "goal_type": g.goal_type,
                    "calorie_target_kcal": g.calorie_target_kcal,
                    "protein_target_g": _dec(g.protein_target_g),
                    "fat_target_g": _dec(g.fat_target_g),
                    "carbohydrate_target_g": _dec(g.carbohydrate_target_g),
                    "status": g.status,
                    "nutrition_policy_version": getattr(
                        g, "nutrition_policy_version", None
                    ),
                }
                for g in goals
            ],
            "preferences": [
                {"name": p.display_name, "type": p.preference_type} for p in prefs
            ],
            "restrictions": [
                {"name": r.display_name, "type": r.restriction_type} for r in restrictions
            ],
            "pantry": [
                {
                    "name": p.display_name,
                    "quantity_value": _dec(p.quantity_value),
                    "unit": p.unit,
                }
                for p in pantry
            ],
            "weight_entries": [
                {
                    "weight_kg": _dec(w.weight_kg),
                    "measured_at": w.measured_at.isoformat(),
                    "note": w.note,
                }
                for w in weights
            ],
            "nutrition_logs": nutrition_logs,
            "water_entries": water_entries,
            "meal_plans": [
                {
                    "id": str(p.id),
                    "start_date": p.start_date.isoformat(),
                    "end_date": p.end_date.isoformat(),
                    "status": p.status,
                    "calorie_target_kcal": p.calorie_target_kcal,
                }
                for p in plans
            ],
            "meal_plan_items": [
                {
                    "id": str(i.id),
                    "meal_plan_id": str(i.meal_plan_id),
                    "recipe_id": str(i.recipe_id),
                    "planned_date": i.planned_date.isoformat(),
                    "meal_type": i.meal_type,
                    "is_completed": i.is_completed,
                    "calories_kcal": i.calories_kcal,
                }
                for i in items
            ],
            "shopping_lists": [
                {
                    "id": str(s.id),
                    "from_date": s.from_date.isoformat(),
                    "to_date": s.to_date.isoformat(),
                    "status": s.status,
                }
                for s in shopping
            ],
            "shopping_list_items": [
                {
                    "display_name": si.display_name,
                    "quantity_value": _dec(si.quantity_value),
                    "unit": si.unit,
                    "is_completed": si.is_completed,
                }
                for si in shopping_items
            ],
            "chat": {
                "conversations": [
                    {"id": str(c.id), "title": c.title, "status": c.status}
                    for c in conversations
                ],
                "messages": [
                    {
                        "conversation_id": str(m.conversation_id),
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                ],
            },
            "favorites": [{"recipe_id": str(f.recipe_id)} for f in favorites],
        }

    async def delete_account(self, user: User, *, confirmation: str) -> None:
        if confirmation.strip().upper() != "DELETE":
            raise DeleteConfirmationRequired()
        user_id = user.id
        await self._auth.revoke_all_for_user(user_id, at=utcnow())
        plan_ids = select(MealPlan.id).where(MealPlan.user_id == user_id)
        await self._session.execute(
            delete(MealPlanItem).where(MealPlanItem.meal_plan_id.in_(plan_ids))
        )
        await self._session.execute(
            delete(MealPlan).where(MealPlan.user_id == user_id)
        )
        recipe_ids = select(Recipe.id).where(Recipe.created_by_user_id == user_id)
        await self._session.execute(
            delete(UserRecipeFavorite).where(
                UserRecipeFavorite.recipe_id.in_(recipe_ids)
            )
        )
        await self._session.execute(
            delete(Recipe).where(Recipe.created_by_user_id == user_id)
        )
        # Cascade deletes remaining user-owned rows; shared originals remain.
        await self._auth.delete_user(user)
        await self._session.commit()
        logger.info("account_deleted", extra={"user_id": str(user_id)})
