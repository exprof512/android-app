"""Unified AI context builder — no PII, secrets, or raw prompts."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.versions import AI_CONTEXT_SCHEMA_VERSION
from app.core.config import Settings
from app.core.user_time import local_today_for_user
from app.meal_plans.models import MealPlan, MealPlanItem
from app.meal_plans.selection import find_ready_covering
from app.nutrition.day_balance import compute_day_consumed
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from app.recipes.models import Recipe
from app.recipes.repository import RecipeRepository

_ALLOWED_INGREDIENTS_MAX = 400
_RECENT_RECIPES_MAX = 20
_SENSITIVE_KEYS = frozenset(
    {
        "email",
        "password",
        "password_hash",
        "jwt",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "authorization",
    }
)


class AIContextBuilder:
    """Build a minimal, sanitized context dict for Text AI operations."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings

    async def build(
        self,
        user_id: UUID,
        session: AsyncSession | None = None,
        *,
        intent: str | None = None,
        meal_plan_item_id: UUID | None = None,
        recipe_id: UUID | None = None,
        on_date: date | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Assemble user-scoped AI context. Never includes email/password/JWT."""
        db = session or self._session
        from app.core.user_time import local_today_for_user
        from app.meal_plans.selection import find_ready_covering
        from app.nutrition.day_balance import compute_day_consumed

        day = on_date or await local_today_for_user(db, user_id)
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        ).scalar_one_or_none()
        goal = None
        if profile is not None and profile.active_goal_id is not None:
            goal = await db.get(Goal, profile.active_goal_id)
        preference_rows = list(
            (
                await db.execute(
                    select(FoodPreference).where(FoodPreference.user_id == user_id)
                )
            ).scalars()
        )
        restrictions_rows = list(
            (
                await db.execute(
                    select(FoodRestriction).where(FoodRestriction.user_id == user_id)
                )
            ).scalars()
        )
        pantry_rows = list(
            (
                await db.execute(
                    select(AvailableProduct).where(AvailableProduct.user_id == user_id)
                )
            ).scalars()
        )

        nutrition_policy_version = "v1"
        if goal is not None:
            nutrition_policy_version = getattr(goal, "nutrition_policy_version", "v1")
        elif self._settings is not None:
            nutrition_policy_version = self._settings.nutrition_policy_version

        targets = None
        if goal is not None:
            targets = {
                "calorie_target_kcal": goal.calorie_target_kcal,
                "protein_target_g": float(goal.protein_target_g),
                "fat_target_g": float(goal.fat_target_g),
                "carbohydrate_target_g": float(goal.carbohydrate_target_g),
            }

        plan, plan_meals = await self._plan_meals_for_day(db, user_id, day)
        balance = await compute_day_consumed(
            db, user_id=user_id, on_date=day, plan=plan
        )
        target_kcal = (
            plan.calorie_target_kcal
            if plan is not None
            else (targets or {}).get("calorie_target_kcal") or 0
        )
        consumed_remaining = {
            "consumed_kcal": balance.consumed_kcal,
            "consumed_protein_g": float(balance.protein_g),
            "consumed_fat_g": float(balance.fat_g),
            "consumed_carbohydrate_g": float(balance.carbs_g),
            "remaining_kcal": max(0, int(target_kcal) - balance.consumed_kcal),
            "from_diary_kcal": balance.from_diary_kcal,
            "from_plan_kcal": balance.from_plan_kcal,
        }

        restrictions = [
            r.display_name
            for r in restrictions_rows
            if r.restriction_type in {"allergy", "excluded", "dietary"}
        ][:40]
        preferences = {
            "liked": [
                p.display_name
                for p in preference_rows
                if p.preference_type == "liked"
            ][:30],
            "disliked": [
                p.display_name
                for p in preference_rows
                if p.preference_type == "disliked"
            ][:30],
        }
        pantry = [p.display_name for p in pantry_rows][:60]
        recent = await self._recent_completed_recipes(db, user_id)
        allowed = await RecipeRepository(db).active_canonical_names()
        allowed = allowed[:_ALLOWED_INGREDIENTS_MAX]

        focus_recipe_name = None
        if recipe_id is not None:
            recipe = await db.get(Recipe, recipe_id)
            focus_recipe_name = recipe.name if recipe else None

        focus_item = None
        if meal_plan_item_id is not None:
            item = await db.get(MealPlanItem, meal_plan_item_id)
            if item is not None:
                recipe = await db.get(Recipe, item.recipe_id)
                focus_item = {
                    "meal_type": item.meal_type,
                    "planned_date": item.planned_date.isoformat(),
                    "recipe_id": str(item.recipe_id),
                    "recipe_name": recipe.name if recipe else None,
                    "is_completed": item.is_completed,
                }

        context: dict[str, Any] = {
            "locale": "ru-RU",
            "context_version": AI_CONTEXT_SCHEMA_VERSION,
            "nutrition_policy_version": nutrition_policy_version,
            "intent": intent,
            "on_date": day.isoformat(),
            "goal": (
                {
                    "type": goal.goal_type,
                    "calorie_target_kcal": goal.calorie_target_kcal,
                }
                if goal
                else None
            ),
            "targets": targets,
            "consumed_today": consumed_remaining.get("consumed"),
            "remaining_today": consumed_remaining.get("remaining"),
            "plan_meals": [
                {
                    "meal_type": m["meal_type"],
                    "recipe_id": m["recipe_id"],
                    "name": m["name"],
                    "is_completed": m["is_completed"],
                    "calories_kcal": m.get("calories_kcal"),
                }
                for m in plan_meals
            ],
            "preferences": preferences,
            "restrictions": restrictions,
            "pantry": pantry,
            "recent_recipes": recent,
            "recent_recipe_ids": [r["id"] for r in recent],
            "max_cook_time_minutes": (
                profile.max_cook_time_minutes if profile else None
            ),
            "grocery_budget_weekly": (
                float(profile.grocery_budget_weekly)
                if profile and profile.grocery_budget_weekly is not None
                else None
            ),
            "currency": (profile.currency if profile else None) or "RUB",
            "meals_per_day": profile.meals_per_day if profile else None,
            "allowed_ingredients": allowed,
            "focus_recipe_name": focus_recipe_name,
            "focus_meal_item": focus_item,
        }
        if extra:
            for key, value in extra.items():
                if key.lower() in _SENSITIVE_KEYS:
                    continue
                context[key] = value
        return _sanitize(context)

    async def _plan_meals_for_day(
        self, db: AsyncSession, user_id: UUID, day: date
    ) -> tuple[MealPlan | None, list[dict[str, Any]]]:
        plan = await find_ready_covering(db, user_id, day)
        if plan is None:
            return None, []
        items = list(
            (
                await db.execute(
                    select(MealPlanItem).where(
                        MealPlanItem.meal_plan_id == plan.id,
                        MealPlanItem.planned_date == day,
                    )
                )
            ).scalars()
        )
        meals: list[dict[str, Any]] = []
        for item in items:
            recipe = await db.get(Recipe, item.recipe_id)
            meals.append(
                {
                    "meal_type": item.meal_type,
                    "recipe_id": str(item.recipe_id),
                    "name": recipe.name if recipe else "Блюдо",
                    "is_completed": item.is_completed,
                    "calories_kcal": item.calories_kcal,
                    "protein_g": float(item.protein_g),
                    "fat_g": float(item.fat_g),
                    "carbohydrate_g": float(item.carbohydrate_g),
                }
            )
        return plan, meals

    @staticmethod
    def _consumed_remaining(
        plan: MealPlan | None,
        meals: list[dict[str, Any]],
        targets: dict[str, Any] | None,
    ) -> dict[str, Any]:
        completed = [m for m in meals if m.get("is_completed")]
        consumed_kcal = sum(int(m.get("calories_kcal") or 0) for m in completed)
        consumed_protein = sum(float(m.get("protein_g") or 0) for m in completed)
        consumed_fat = sum(float(m.get("fat_g") or 0) for m in completed)
        consumed_carbs = sum(float(m.get("carbohydrate_g") or 0) for m in completed)
        target_kcal = (
            plan.calorie_target_kcal
            if plan is not None
            else (targets or {}).get("calorie_target_kcal") or 0
        )
        target_protein = float(
            plan.protein_target_g
            if plan is not None
            else (targets or {}).get("protein_target_g") or 0
        )
        target_fat = float(
            plan.fat_target_g
            if plan is not None
            else (targets or {}).get("fat_target_g") or 0
        )
        target_carbs = float(
            plan.carbohydrate_target_g
            if plan is not None
            else (targets or {}).get("carbohydrate_target_g") or 0
        )
        return {
            "consumed": {
                "calories_kcal": consumed_kcal,
                "protein_g": round(consumed_protein, 2),
                "fat_g": round(consumed_fat, 2),
                "carbohydrate_g": round(consumed_carbs, 2),
            },
            "remaining": {
                "calories_kcal": max(0, int(target_kcal) - consumed_kcal),
                "protein_g": round(max(0.0, target_protein - consumed_protein), 2),
                "fat_g": round(max(0.0, target_fat - consumed_fat), 2),
                "carbohydrate_g": round(max(0.0, target_carbs - consumed_carbs), 2),
            },
        }

    async def _recent_completed_recipes(
        self, db: AsyncSession, user_id: UUID
    ) -> list[dict[str, str]]:
        statement = (
            select(MealPlanItem, Recipe)
            .join(MealPlan, MealPlanItem.meal_plan_id == MealPlan.id)
            .join(Recipe, MealPlanItem.recipe_id == Recipe.id)
            .where(
                MealPlan.user_id == user_id,
                MealPlanItem.is_completed.is_(True),
            )
            .order_by(MealPlanItem.updated_at.desc())
            .limit(_RECENT_RECIPES_MAX)
        )
        rows = (await db.execute(statement)).all()
        seen: set[str] = set()
        result: list[dict[str, str]] = []
        for item, recipe in rows:
            rid = str(recipe.id)
            if rid in seen:
                continue
            seen.add(rid)
            result.append({"id": rid, "name": recipe.name})
        return result[:_RECENT_RECIPES_MAX]


def _sanitize(value: Any) -> Any:
    """Drop sensitive keys recursively; keep structure otherwise."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                continue
            out[key] = _sanitize(item)
        return out
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
