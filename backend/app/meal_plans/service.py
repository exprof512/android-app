"""MealPlanService: generate, read, replace and complete meal plans."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drafts import recipe_candidate_to_draft
from app.ai.errors import TextAIQuotaExhausted, TextAIUnavailable, TextAIValidationFailed
from app.ai.fallback_plans import build_catalog_meal_plan_proposal
from app.ai.service import TextAIService
from app.core.errors import OwnershipDenied
from app.core.models import utcnow
from app.images.service import ImageGenerationService
from app.meal_plans import constants
from app.meal_plans.engine import DayTargets, MealPlanEngine, PlannedSlot
from app.meal_plans.errors import (
    MealPlanItemNotFound,
    MealPlanNotFound,
    PlanConstraintsUnsatisfied,
    ProfileIncomplete,
)
from app.meal_plans.models import MealPlan, MealPlanItem
from app.meal_plans.repository import MealPlanRepository
from app.meal_plans.schemas import (
    DailyTargetsOut,
    DayProgressOut,
    MacroProgressOut,
    MealPlanGenerateRequest,
    MealPlanItemOut,
    MealPlanOut,
    MealPlanRecipeSummary,
    MealPlanRegenerateRequest,
    WeekDayOut,
    WeekSummaryOut,
)
from app.nutrition.diary import NutritionDiaryService
from app.profiles.service import ProfileService
from app.entitlements import constants as entitlement_constants
from app.entitlements.service import EntitlementsService
from app.recipes.engine import RecipeEngine
from app.recipes.errors import RecipeValidationError
from app.recipes.models import Recipe
from app.recipes.service import RecipeService
from app.recipes.repository import RecipeRepository

logger = logging.getLogger(__name__)

_MEAL_TYPE_RU = {
    "breakfast": "завтрак",
    "lunch": "обед",
    "dinner": "ужин",
    "snack": "перекус",
}


def _scale(value: Decimal | int | float, servings: Decimal) -> Decimal:
    return (Decimal(str(value)) * servings).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _scale_kcal(value: int, servings: Decimal) -> int:
    return int((_scale(value, servings)).to_integral_value(rounding=ROUND_HALF_UP))


class MealPlanService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: MealPlanRepository,
        profile_service: ProfileService,
        recipe_service: RecipeService,
        recipe_engine: RecipeEngine,
        meal_plan_engine: MealPlanEngine,
        text_ai: TextAIService,
        ai_model: str,
        image_service: ImageGenerationService | None = None,
        entitlements: EntitlementsService | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._profiles = profile_service
        self._recipes = recipe_service
        self._recipe_engine = recipe_engine
        self._engine = meal_plan_engine
        self._text_ai = text_ai
        self._ai_model = ai_model
        self._images = image_service
        self._entitlements = entitlements

    async def generate(
        self,
        user_id: UUID,
        payload: MealPlanGenerateRequest,
        *,
        charge_entitlement: bool = True,
    ) -> MealPlanOut:
        snapshot = await self._profiles.get_snapshot(user_id)
        if snapshot.goal is None or snapshot.profile.meals_per_day is None:
            raise ProfileIncomplete()

        end_date = payload.start_date + timedelta(days=payload.days - 1)
        meals_per_day = snapshot.profile.meals_per_day or 3
        request_hash = self._request_hash(
            user_id=user_id,
            goal_id=snapshot.goal.id,
            start_date=payload.start_date,
            days=payload.days,
            notes=payload.notes,
            force_nonce=str(utcnow().timestamp()) if payload.force else None,
        )
        if not payload.force:
            existing = await self._repository.get_by_hash(user_id, request_hash)
            if existing is not None:
                return await self._to_out(existing, warnings=[], reused=True)
        else:
            await self._archive_overlapping(
                user_id, start_date=payload.start_date, end_date=end_date
            )

        # Continuity auto-generate must not burn Free daily quota on Today open.
        if charge_entitlement and self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_MEAL_PLAN_GENERATE
            )

        context = await self._build_generation_context(
            snapshot=snapshot,
            start_date=payload.start_date,
            end_date=end_date,
            notes=payload.notes,
        )
        warnings: list[str] = []
        try:
            proposal = await self._text_ai.generate_meal_plan_proposal(
                context=context, user_id=user_id, use_cache=not payload.force
            )
        except (TextAIQuotaExhausted, TextAIUnavailable, TextAIValidationFailed) as exc:
            logger.warning(
                "meal_plan_ai_fallback",
                extra={"error_code": getattr(exc, "code", "ai_generation_unavailable")},
            )
            proposal = await build_catalog_meal_plan_proposal(
                self._session,
                start_date=payload.start_date,
                end_date=end_date,
                meals_per_day=meals_per_day,
            )
            warnings.append(
                "План собран из каталога: AI временно недоступен."
            )

        if not self._proposal_covers_range(
            proposal,
            start_date=payload.start_date,
            end_date=end_date,
            meals_per_day=meals_per_day,
        ):
            logger.warning(
                "meal_plan_incomplete_slots_fallback",
                extra={"error_code": "incomplete_slots"},
            )
            proposal = await build_catalog_meal_plan_proposal(
                self._session,
                start_date=payload.start_date,
                end_date=end_date,
                meals_per_day=meals_per_day,
            )
            warnings.append(
                f"План дополнен из каталога: нужно {payload.days}×{meals_per_day} приёмов."
            )

        stored_recipes, proposal = await self._persist_proposal_recipes(
            proposal=proposal,
            warnings=warnings,
            start_date=payload.start_date,
            end_date=end_date,
            meals_per_day=meals_per_day,
        )

        targets = DayTargets(
            calories_kcal=snapshot.goal.calorie_target_kcal,
            protein_g=snapshot.goal.protein_target_g,
            fat_g=snapshot.goal.fat_target_g,
            carbohydrate_g=snapshot.goal.carbohydrate_target_g,
        )
        restricted = [
            item.display_name
            for item in snapshot.restrictions
            if item.restriction_type in {"allergy", "excluded"}
        ]

        try:
            slots = self._slots_from_proposal(proposal, stored_recipes)
            warnings = self._engine.validate_plan(
                slots=slots,
                targets=targets,
                meals_per_day=snapshot.profile.meals_per_day,
                max_cook_time_minutes=snapshot.profile.max_cook_time_minutes,
                restricted_names=restricted,
                start_date=payload.start_date,
                end_date=end_date,
            ) + warnings
        except PlanConstraintsUnsatisfied as exc:
            logger.warning(
                "meal_plan_constraints_fallback",
                extra={
                    "error_code": "plan_constraints_unsatisfied",
                    "detail_count": len(getattr(exc, "details", None) or []),
                },
            )
            proposal = await build_catalog_meal_plan_proposal(
                self._session,
                start_date=payload.start_date,
                end_date=end_date,
                meals_per_day=meals_per_day,
            )
            warnings.append(
                "План собран из каталога: AI-предложение не прошло проверку питания."
            )
            stored_recipes, proposal = await self._persist_proposal_recipes(
                proposal=proposal,
                warnings=warnings,
                start_date=payload.start_date,
                end_date=end_date,
                meals_per_day=meals_per_day,
            )
            slots = self._slots_from_proposal(proposal, stored_recipes)
            warnings = self._engine.validate_plan(
                slots=slots,
                targets=targets,
                meals_per_day=snapshot.profile.meals_per_day,
                max_cook_time_minutes=snapshot.profile.max_cook_time_minutes,
                restricted_names=restricted,
                start_date=payload.start_date,
                end_date=end_date,
            ) + warnings

        plan = MealPlan(
            user_id=user_id,
            goal_id=snapshot.goal.id,
            start_date=payload.start_date,
            end_date=end_date,
            status="ready",
            calorie_target_kcal=snapshot.goal.calorie_target_kcal,
            protein_target_g=snapshot.goal.protein_target_g,
            fat_target_g=snapshot.goal.fat_target_g,
            carbohydrate_target_g=snapshot.goal.carbohydrate_target_g,
            generation_request_hash=request_hash,
            nutrition_policy_version=getattr(
                snapshot.goal, "nutrition_policy_version", "v1"
            ),
            items=[self._build_item(slot) for slot in slots],
        )
        await self._repository.add_plan(plan)
        await self._session.commit()
        await self._session.refresh(plan)
        if self._images is not None:
            seen: set = set()
            for recipe in stored_recipes:
                if recipe.id in seen:
                    continue
                seen.add(recipe.id)
                try:
                    await self._images.enqueue_for_recipe(
                        recipe.id, user_id=user_id
                    )
                except Exception:
                    logger.warning(
                        "image_enqueue_failed",
                        extra={"recipe_id": str(recipe.id), "error_code": "image_enqueue"},
                    )
        return await self._to_out(plan, warnings=warnings, reused=False)

    async def today(self, user_id: UUID, on_date: date) -> MealPlanOut:
        """Return today's plan, generating one if missing (idempotent continuity)."""
        plan = await self.ensure_current_day_plan(user_id, on_date)
        items = await self._repository.list_items_for_dates(
            plan.id, from_date=on_date, to_date=on_date
        )
        out = await self._to_out(
            plan,
            warnings=[],
            items_override=items,
            day_progress_date=on_date,
            include_week_summary=False,
        )
        await self._maybe_prepare_next_week(user_id, plan, on_date)
        # Reload day items in case next-week gen archived something (should not).
        return out

    async def ensure_current_day_plan(self, user_id: UUID, on_date: date) -> MealPlan:
        """Idempotent: return covering plan or generate a 7-day window from on_date."""
        plan = await self._repository.find_covering(user_id, on_date=on_date)
        if plan is not None:
            return plan
        logger.info(
            "ensure_current_day_plan_generate",
            extra={"user_id": str(user_id), "on_date": on_date.isoformat()},
        )
        try:
            generated = await self.generate(
                user_id,
                MealPlanGenerateRequest(start_date=on_date, days=7, force=False),
                charge_entitlement=False,
            )
        except Exception:
            # Concurrent GET /today may race; prefer covering plan if another won.
            plan = await self._repository.find_covering(user_id, on_date=on_date)
            if plan is not None:
                return plan
            raise
        plan = await self._repository.get_plan(generated.id)
        if plan is None:
            plan = await self._repository.find_covering(user_id, on_date=on_date)
        if plan is None:
            raise MealPlanNotFound()
        return plan

    async def _maybe_prepare_next_week(
        self, user_id: UUID, plan: MealPlan, on_date: date
    ) -> None:
        """When ≤1 day remains in the active plan, ensure the next 7-day window exists."""
        days_remaining = (plan.end_date - on_date).days
        if days_remaining > 1:
            return
        next_start = plan.end_date + timedelta(days=1)
        existing = await self._repository.find_covering(user_id, on_date=next_start)
        if existing is not None:
            return
        try:
            logger.info(
                "ensure_next_week_plan_generate",
                extra={
                    "user_id": str(user_id),
                    "next_start": next_start.isoformat(),
                },
            )
            await self.generate(
                user_id,
                MealPlanGenerateRequest(start_date=next_start, days=7, force=False),
                charge_entitlement=False,
            )
        except Exception:
            logger.warning(
                "ensure_next_week_plan_failed",
                extra={"user_id": str(user_id), "error_code": "next_week_generate"},
                exc_info=True,
            )

    async def week(self, user_id: UUID, start_date: date) -> MealPlanOut:
        plan = await self.ensure_current_day_plan(user_id, start_date)
        # Always return the full active plan window (typically 7 days),
        # not only [request_date .. request_date+6] which collapses to "today"
        # when the plan ends on that day.
        items = await self._repository.list_items_for_dates(
            plan.id, from_date=plan.start_date, to_date=plan.end_date
        )
        return await self._to_out(
            plan,
            warnings=[],
            items_override=items,
            include_week_summary=True,
        )

    async def regenerate(
        self, user_id: UUID, plan_id: UUID, payload: MealPlanRegenerateRequest
    ) -> MealPlanOut:
        plan = await self._repository.get_plan(plan_id)
        if plan is None:
            raise MealPlanNotFound()
        if plan.user_id != user_id:
            raise OwnershipDenied()
        # Full regenerate: archive hash uniqueness by clearing old hash and generating anew.
        days = (plan.end_date - plan.start_date).days + 1
        if payload.scope == "day":
            if payload.on_date is None:
                raise PlanConstraintsUnsatisfied(
                    [{"field": "date", "reason": "required_for_day_scope"}]
                )
            start = payload.on_date
            days = 1
        else:
            start = plan.start_date
        await self._mark_shopping_stale(plan.id)
        plan.status = "archived"
        plan.generation_request_hash = None
        await self._session.flush()
        return await self.generate(
            user_id,
            MealPlanGenerateRequest(
                start_date=start, days=days, notes=payload.notes, force=True
            ),
        )

    async def replace_item(
        self,
        user_id: UUID,
        item_id: UUID,
        *,
        replace_reason: str = "user_requested",
        idempotency_key: str | None = None,
    ) -> MealPlanOut:
        if idempotency_key:
            cached = await self._load_idempotent_replace(user_id, idempotency_key)
            if cached is not None:
                return cached

        item = await self._repository.get_item(item_id)
        if item is None:
            raise MealPlanItemNotFound()
        plan = await self._repository.get_plan(item.meal_plan_id)
        if plan is None:
            raise MealPlanNotFound()
        if plan.user_id != user_id:
            raise OwnershipDenied()

        if self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_MEAL_REPLACE
            )

        snapshot = await self._profiles.get_snapshot(user_id)
        if snapshot.goal is None:
            raise ProfileIncomplete()

        restricted = [
            r.display_name
            for r in snapshot.restrictions
            if r.restriction_type in {"allergy", "excluded"}
        ]
        allowed = await RecipeRepository(self._session).active_canonical_names()
        day_items = await self._repository.list_items_for_dates(
            plan.id, from_date=item.planned_date, to_date=item.planned_date
        )
        consumed_kcal = sum(
            i.calories_kcal for i in day_items if i.is_completed and i.id != item.id
        )
        remaining_kcal = max(0, plan.calorie_target_kcal - consumed_kcal)
        pantry_names = [p.display_name for p in snapshot.pantry]
        context = {
            "locale": "ru-RU",
            "meal_type": item.meal_type,
            "planned_date": item.planned_date.isoformat(),
            "calorie_target_kcal": snapshot.goal.calorie_target_kcal,
            "remaining_day_calories_kcal": remaining_kcal,
            "protein_target_g": float(snapshot.goal.protein_target_g),
            "fat_target_g": float(snapshot.goal.fat_target_g),
            "carbohydrate_target_g": float(snapshot.goal.carbohydrate_target_g),
            "max_cook_time_minutes": snapshot.profile.max_cook_time_minutes,
            "grocery_budget_weekly": (
                float(snapshot.profile.grocery_budget_weekly)
                if snapshot.profile.grocery_budget_weekly is not None
                else None
            ),
            "restrictions": restricted,
            "liked_foods": [
                p.display_name
                for p in snapshot.preferences
                if p.preference_type == "liked"
            ],
            "disliked_foods": [
                p.display_name
                for p in snapshot.preferences
                if p.preference_type == "disliked"
            ],
            "pantry": pantry_names,
            "allowed_ingredients": allowed,
            "replace_recipe_name": item.recipe.name if item.recipe else None,
            "replace_reason": replace_reason,
        }
        fallback_warnings: list[str] = []
        try:
            replacement = await self._text_ai.replace_meal_item(
                context=context, user_id=user_id, use_cache=False
            )
            candidate = replacement.recipes[0]
            draft = recipe_candidate_to_draft(candidate, ai_model=self._ai_model)
            try:
                stored = await self._recipes.create_recipe(draft)
            except RecipeValidationError:
                logger.warning(
                    "replace_meal_recipe_validation_fallback",
                    extra={"error_code": "recipe_validation_error"},
                )
                fallback = await build_catalog_meal_plan_proposal(
                    self._session,
                    start_date=item.planned_date,
                    end_date=item.planned_date,
                    meals_per_day=1,
                )
                candidate = fallback.recipes[0].model_copy(
                    update={"name": f"Замена: {fallback.recipes[0].name}"}
                )
                draft = recipe_candidate_to_draft(candidate, ai_model=self._ai_model)
                stored = await self._recipes.create_recipe(draft)
                fallback_warnings.append(
                    "Замена из каталога: AI предложил неизвестные ингредиенты."
                )
        except (TextAIQuotaExhausted, TextAIUnavailable):
            logger.warning(
                "replace_meal_ai_fallback",
                extra={"error_code": "ai_generation_unavailable"},
            )
            fallback = await build_catalog_meal_plan_proposal(
                self._session,
                start_date=item.planned_date,
                end_date=item.planned_date,
                meals_per_day=1,
            )
            candidate = fallback.recipes[0].model_copy(
                update={"name": f"Замена: {fallback.recipes[0].name}"}
            )
            draft = recipe_candidate_to_draft(candidate, ai_model=self._ai_model)
            stored = await self._recipes.create_recipe(draft)
            fallback_warnings.append(
                "Замена из каталога: AI временно недоступен."
            )
        recipe = stored.recipe

        slot = PlannedSlot(
            planned_date=item.planned_date,
            meal_type=item.meal_type,
            sort_order=item.sort_order,
            servings=item.servings,
            recipe=recipe,
        )
        targets = DayTargets(
            calories_kcal=plan.calorie_target_kcal,
            protein_g=plan.protein_target_g,
            fat_g=plan.fat_target_g,
            carbohydrate_g=plan.carbohydrate_target_g,
        )
        # Validate the single replaced day with other items kept.
        day_items = await self._repository.list_items_for_dates(
            plan.id, from_date=item.planned_date, to_date=item.planned_date
        )
        slots = []
        for existing in day_items:
            if existing.id == item.id:
                slots.append(slot)
            else:
                slots.append(
                    PlannedSlot(
                        planned_date=existing.planned_date,
                        meal_type=existing.meal_type,
                        sort_order=existing.sort_order,
                        servings=existing.servings,
                        recipe=existing.recipe,
                    )
                )
        warnings = fallback_warnings + self._engine.validate_plan(
            slots=slots,
            targets=targets,
            meals_per_day=len(slots),
            max_cook_time_minutes=snapshot.profile.max_cook_time_minutes,
            restricted_names=restricted,
            start_date=item.planned_date,
            end_date=item.planned_date,
        )

        item.recipe_id = recipe.id
        item.recipe = recipe
        item.calories_kcal = _scale_kcal(recipe.calories_kcal, item.servings)
        item.protein_g = _scale(recipe.protein_g, item.servings)
        item.fat_g = _scale(recipe.fat_g, item.servings)
        item.carbohydrate_g = _scale(recipe.carbohydrate_g, item.servings)
        item.estimated_cost_amount = _scale(recipe.estimated_cost_amount, item.servings)
        # Keep completion semantics: replaced-but-eaten stays completed with synced diary.
        if item.is_completed or item.status == "completed":
            item.status = "completed"
            item.is_completed = True
            diary = NutritionDiaryService(self._session)
            await diary.upsert_from_meal_plan_item(user_id, item, commit=False)
        else:
            item.status = "replaced"
            item.is_completed = False
        await self._mark_shopping_stale(plan.id)
        await self._session.commit()
        await self._session.refresh(item)
        if self._images is not None:
            try:
                await self._images.enqueue_for_recipe(recipe.id, user_id=user_id)
            except Exception:
                logger.warning(
                    "image_enqueue_failed",
                    extra={"recipe_id": str(recipe.id), "error_code": "image_enqueue"},
                )
        refreshed = await self._repository.get_plan(plan.id)
        assert refreshed is not None
        out = await self._to_out(refreshed, warnings=warnings)
        if idempotency_key:
            await self._store_idempotent_replace(user_id, idempotency_key, out)
        return out

    async def _load_idempotent_replace(
        self, user_id: UUID, key: str
    ) -> MealPlanOut | None:
        from datetime import timedelta

        from sqlalchemy import select

        from app.auth.models import IdempotencyKey
        from app.core.models import as_utc, utcnow

        row = (
            await self._session.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.user_id == user_id,
                    IdempotencyKey.endpoint == "meal_replace",
                    IdempotencyKey.key == key,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        if as_utc(row.expires_at) <= utcnow():
            return None
        if row.response_body:
            return MealPlanOut.model_validate(row.response_body)
        return None

    async def _store_idempotent_replace(
        self, user_id: UUID, key: str, out: MealPlanOut
    ) -> None:
        from datetime import timedelta

        from app.auth.models import IdempotencyKey
        from app.core.models import utcnow
        import hashlib

        body = out.model_dump(mode="json")
        digest = hashlib.sha256(
            str(body.get("id", "")).encode("utf-8")
        ).hexdigest()
        existing = await self._load_idempotent_replace(user_id, key)
        if existing is not None:
            return
        row = IdempotencyKey(
            user_id=user_id,
            key=key[:255],
            endpoint="meal_replace",
            request_hash=digest,
            response_status=200,
            response_body=body,
            expires_at=utcnow() + timedelta(hours=24),
        )
        self._session.add(row)
        await self._session.commit()

    async def complete_item(
        self, user_id: UUID, item_id: UUID, *, completed: bool = True
    ) -> MealPlanItemOut:
        item = await self._repository.get_item(item_id)
        if item is None:
            raise MealPlanItemNotFound()
        plan = await self._repository.get_plan(item.meal_plan_id)
        if plan is None:
            raise MealPlanNotFound()
        if plan.user_id != user_id:
            raise OwnershipDenied()
        diary = NutritionDiaryService(self._session)
        if completed:
            item.is_completed = True
            item.completed_at = utcnow()
            item.status = "completed"
            await diary.upsert_from_meal_plan_item(user_id, item, commit=False)
        else:
            item.is_completed = False
            item.completed_at = None
            item.status = "planned"
            await diary.delete_by_meal_plan_item(user_id, item.id, commit=False)
        await self._session.commit()
        await self._session.refresh(item)
        recipe = item.recipe or await self._session.get(Recipe, item.recipe_id)
        assert recipe is not None
        return self._item_out(item, recipe)

    async def skip_item(
        self, user_id: UUID, item_id: UUID, *, skipped: bool = True
    ) -> MealPlanItemOut:
        item = await self._repository.get_item(item_id)
        if item is None:
            raise MealPlanItemNotFound()
        plan = await self._repository.get_plan(item.meal_plan_id)
        if plan is None:
            raise MealPlanNotFound()
        if plan.user_id != user_id:
            raise OwnershipDenied()
        diary = NutritionDiaryService(self._session)
        if skipped:
            item.is_completed = False
            item.completed_at = None
            item.status = "skipped"
            await diary.delete_by_meal_plan_item(user_id, item.id, commit=False)
        else:
            item.is_completed = False
            item.completed_at = None
            item.status = "planned"
        await self._session.commit()
        await self._session.refresh(item)
        recipe = item.recipe or await self._session.get(Recipe, item.recipe_id)
        assert recipe is not None
        return self._item_out(item, recipe)

    async def _mark_shopping_stale(self, meal_plan_id: UUID) -> None:
        from sqlalchemy import select

        from app.shopping.models import ShoppingList

        rows = list(
            (
                await self._session.execute(
                    select(ShoppingList).where(
                        ShoppingList.meal_plan_id == meal_plan_id,
                        ShoppingList.status == "ready",
                    )
                )
            ).scalars()
        )
        for row in rows:
            row.stale = True

    def _build_item(self, slot: PlannedSlot) -> MealPlanItem:
        return MealPlanItem(
            recipe_id=slot.recipe.id,
            planned_date=slot.planned_date,
            meal_type=slot.meal_type,
            servings=slot.servings,
            sort_order=slot.sort_order,
            status="planned",
            is_completed=False,
            calories_kcal=_scale_kcal(slot.recipe.calories_kcal, slot.servings),
            protein_g=_scale(slot.recipe.protein_g, slot.servings),
            fat_g=_scale(slot.recipe.fat_g, slot.servings),
            carbohydrate_g=_scale(slot.recipe.carbohydrate_g, slot.servings),
            estimated_cost_amount=_scale(
                slot.recipe.estimated_cost_amount, slot.servings
            ),
        )

    async def _persist_proposal_recipes(
        self,
        *,
        proposal,
        warnings: list[str],
        start_date: date,
        end_date: date,
        meals_per_day: int,
    ) -> tuple[list[Recipe], object]:
        """Persist AI recipes; on unknown ingredients fall back to catalog templates."""
        try:
            stored_recipes: list[Recipe] = []
            for candidate in proposal.recipes:
                draft = recipe_candidate_to_draft(candidate, ai_model=self._ai_model)
                stored = await self._recipes.create_recipe(draft)
                stored_recipes.append(stored.recipe)
            return stored_recipes, proposal
        except RecipeValidationError as exc:
            logger.warning(
                "meal_plan_recipe_validation_fallback",
                extra={
                    "error_code": "recipe_validation_error",
                    "detail_count": len(exc.details or []),
                },
            )
            warnings.append(
                "План собран из каталога: AI предложил продукты вне справочника."
            )
            proposal = await build_catalog_meal_plan_proposal(
                self._session,
                start_date=start_date,
                end_date=end_date,
                meals_per_day=meals_per_day,
            )
            stored_recipes = []
            for candidate in proposal.recipes:
                draft = recipe_candidate_to_draft(candidate, ai_model=self._ai_model)
                stored = await self._recipes.create_recipe(draft)
                stored_recipes.append(stored.recipe)
            return stored_recipes, proposal

    async def _build_generation_context(
        self, *, snapshot, start_date: date, end_date: date, notes: str | None
    ) -> dict:
        meals = constants.MEALS_BY_COUNT.get(
            snapshot.profile.meals_per_day or 4, constants.MEALS_BY_COUNT[4]
        )
        days = []
        cursor = start_date
        while cursor <= end_date:
            days.append(
                {
                    "date": cursor.isoformat(),
                    "meal_types": list(meals),
                }
            )
            cursor = cursor + timedelta(days=1)
        allowed = await RecipeRepository(self._session).active_canonical_names()
        return {
            "locale": "ru-RU",
            "calorie_target_kcal": snapshot.goal.calorie_target_kcal,
            "protein_target_g": float(snapshot.goal.protein_target_g),
            "fat_target_g": float(snapshot.goal.fat_target_g),
            "carbohydrate_target_g": float(snapshot.goal.carbohydrate_target_g),
            "meals_per_day": snapshot.profile.meals_per_day,
            "max_cook_time_minutes": snapshot.profile.max_cook_time_minutes,
            "household_size": snapshot.profile.household_size,
            "grocery_budget_weekly": (
                float(snapshot.profile.grocery_budget_weekly)
                if snapshot.profile.grocery_budget_weekly is not None
                else None
            ),
            "currency": snapshot.profile.currency,
            "liked_foods": [
                p.display_name
                for p in snapshot.preferences
                if p.preference_type == "liked"
            ],
            "disliked_foods": [
                p.display_name
                for p in snapshot.preferences
                if p.preference_type == "disliked"
            ],
            "restrictions": [
                r.display_name
                for r in snapshot.restrictions
                if r.restriction_type in {"allergy", "excluded"}
            ],
            "available_products": [p.display_name for p in snapshot.pantry],
            "allowed_ingredients": allowed,
            "days": days,
            "notes": notes,
            "instructions": (
                "Верни recipes[] и slots[]: ДЛЯ КАЖДОГО дня из days и КАЖДОГО "
                "meal_type из day.meal_types ровно один slot. "
                f"Всего слотов должно быть ровно "
                f"{(end_date - start_date).days + 1} × {snapshot.profile.meals_per_day}. "
                "recipe_index указывает на recipes. Не используй запрещённые продукты. "
                "Названия ingredients.name — ТОЛЬКО из allowed_ingredients (как в списке). "
                "Порции servings обычно 1. Калории дня близки к calorie_target_kcal."
            ),
        }

    async def _archive_overlapping(
        self, user_id: UUID, *, start_date: date, end_date: date
    ) -> None:
        """Archive ready plans that overlap the requested range so force regenerate works."""
        cursor = start_date
        seen: set[UUID] = set()
        while cursor <= end_date:
            plan = await self._repository.find_covering(user_id, on_date=cursor)
            if plan is not None and plan.id not in seen:
                seen.add(plan.id)
                plan.status = "archived"
                plan.generation_request_hash = None
            cursor = cursor + timedelta(days=1)
        if seen:
            await self._session.flush()

    @staticmethod
    def _slots_from_proposal(proposal, stored_recipes: list) -> list[PlannedSlot]:
        slots: list[PlannedSlot] = []
        for index, slot in enumerate(proposal.slots):
            if slot.recipe_index >= len(stored_recipes):
                raise PlanConstraintsUnsatisfied(
                    [{"field": "recipe_index", "reason": "out_of_range"}]
                )
            planned = date.fromisoformat(slot.planned_date)
            recipe = stored_recipes[slot.recipe_index]
            slots.append(
                PlannedSlot(
                    planned_date=planned,
                    meal_type=slot.meal_type,
                    sort_order=index,
                    servings=Decimal(str(slot.servings)),
                    recipe=recipe,
                )
            )
        return slots

    @staticmethod
    def _proposal_covers_range(
        proposal,
        *,
        start_date: date,
        end_date: date,
        meals_per_day: int,
    ) -> bool:
        expected = Counter(
            constants.MEALS_BY_COUNT.get(meals_per_day, constants.MEALS_BY_COUNT[4])
        )
        by_day: dict[str, Counter[str]] = {}
        for slot in proposal.slots:
            by_day.setdefault(slot.planned_date, Counter())[slot.meal_type] += 1
        cursor = start_date
        while cursor <= end_date:
            key = cursor.isoformat()
            meals = by_day.get(key, Counter())
            if meals != expected:
                return False
            cursor = cursor + timedelta(days=1)
        return True

    @staticmethod
    def _request_hash(
        *,
        user_id: UUID,
        goal_id: UUID,
        start_date: date,
        days: int,
        notes: str | None,
        force_nonce: str | None = None,
    ) -> str:
        payload = {
            "user_id": str(user_id),
            "goal_id": str(goal_id),
            "start_date": start_date.isoformat(),
            "days": days,
            "notes": notes or "",
        }
        if force_nonce:
            payload["force_nonce"] = force_nonce
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _to_out(
        self,
        plan: MealPlan,
        *,
        warnings: list[str],
        reused: bool = False,
        items_override: list[MealPlanItem] | None = None,
        day_progress_date: date | None = None,
        include_week_summary: bool = False,
    ) -> MealPlanOut:
        items = items_override if items_override is not None else list(plan.items)
        out_items: list[MealPlanItemOut] = []
        for item in items:
            recipe = item.recipe
            if recipe is None:
                recipe = await self._session.get(Recipe, item.recipe_id)
            if recipe is None:
                continue
            image_payload: dict[str, object] = {
                "status": "pending",
                "thumbnail_url": None,
                "url": None,
            }
            if self._images is not None:
                peeked = await self._images.peek_primary(recipe.id)
                if peeked is not None:
                    image_payload = {
                        "id": str(peeked.id),
                        "recipe_id": str(peeked.recipe_id),
                        "status": peeked.status,
                        "url": peeked.url,
                        "thumbnail_url": peeked.thumbnail_url,
                        "retry_allowed": peeked.retry_allowed,
                    }
            out_items.append(self._item_out(item, recipe, image_payload))

        day_progress: DayProgressOut | None = None
        if day_progress_date is not None:
            day_progress = await self._build_day_progress(
                plan, items, on_date=day_progress_date
            )

        week_summary: WeekSummaryOut | None = None
        if include_week_summary:
            all_items = items_override if items_override is not None else list(plan.items)
            if items_override is not None and (
                not all_items
                or min(i.planned_date for i in all_items) > plan.start_date
                or max(i.planned_date for i in all_items) < plan.end_date
            ):
                all_items = await self._repository.list_items_for_dates(
                    plan.id, from_date=plan.start_date, to_date=plan.end_date
                )
            week_summary = self._build_week_summary(plan, all_items)

        return MealPlanOut(
            id=plan.id,
            start_date=plan.start_date,
            end_date=plan.end_date,
            status=plan.status,
            daily_targets=DailyTargetsOut(
                calories_kcal=plan.calorie_target_kcal,
                protein_g=plan.protein_target_g,
                fat_g=plan.fat_target_g,
                carbohydrate_g=plan.carbohydrate_target_g,
            ),
            items=out_items,
            warnings=warnings,
            reused=reused,
            day_progress=day_progress,
            week_summary=week_summary,
        )

    async def _build_day_progress(
        self,
        plan: MealPlan,
        items: list[MealPlanItem],
        *,
        on_date: date,
    ) -> DayProgressOut:
        day_items = [i for i in items if i.planned_date == on_date]
        completed = [i for i in day_items if i.status == "completed" or i.is_completed]
        skipped = [i for i in day_items if i.status == "skipped"]
        open_planned = [
            i
            for i in day_items
            if i.status not in {"completed", "skipped"} and not i.is_completed
        ]
        planned_meals = len(day_items)

        # Invariant: only COMPLETED plan slots contribute from the plan.
        from_plan_kcal = sum(i.calories_kcal for i in completed)
        consumed_kcal = from_plan_kcal
        consumed_protein = sum((i.protein_g for i in completed), Decimal("0"))
        consumed_fat = sum((i.fat_g for i in completed), Decimal("0"))
        consumed_carbs = sum((i.carbohydrate_g for i in completed), Decimal("0"))

        completed_ids = {i.id for i in completed}
        from app.nutrition.models import NutritionLog
        from sqlalchemy import select

        logs = list(
            (
                await self._session.execute(
                    select(NutritionLog).where(
                        NutritionLog.user_id == plan.user_id,
                        NutritionLog.logged_on == on_date,
                    )
                )
            ).scalars()
        )
        from_diary_kcal = 0
        for log in logs:
            if (
                log.meal_plan_item_id is not None
                and log.meal_plan_item_id in completed_ids
            ):
                continue
            from_diary_kcal += log.calories_kcal
            consumed_kcal += log.calories_kcal
            consumed_protein += log.protein_g
            consumed_fat += log.fat_g
            consumed_carbs += log.carbohydrate_g

        target_kcal = plan.calorie_target_kcal
        target_protein = Decimal(str(plan.protein_target_g))
        target_fat = Decimal(str(plan.fat_target_g))
        target_carbs = Decimal(str(plan.carbohydrate_target_g))

        delta = int(consumed_kcal) - target_kcal
        remaining_kcal = max(0, -delta)
        over_target_kcal = max(0, delta)
        planned_remaining_kcal = sum(i.calories_kcal for i in open_planned)

        next_item = next(
            (
                i
                for i in sorted(day_items, key=lambda x: x.sort_order)
                if i.status not in {"completed", "skipped"} and not i.is_completed
            ),
            None,
        )

        daily_cost = sum(
            (i.estimated_cost_amount for i in day_items), Decimal("0")
        ).quantize(Decimal("0.01"))

        suggestions = self._build_suggestions(
            day_items=day_items,
            next_item=next_item,
            remaining_protein=max(Decimal("0"), target_protein - consumed_protein),
            target_protein=target_protein,
        )

        remaining_protein = max(Decimal("0"), target_protein - consumed_protein)
        remaining_fat = max(Decimal("0"), target_fat - consumed_fat)
        remaining_carbs = max(Decimal("0"), target_carbs - consumed_carbs)

        return DayProgressOut(
            consumed_kcal=int(consumed_kcal),
            target_kcal=target_kcal,
            remaining_kcal=remaining_kcal,
            over_target_kcal=over_target_kcal,
            planned_remaining_kcal=planned_remaining_kcal,
            from_plan_kcal=int(from_plan_kcal),
            from_diary_kcal=int(from_diary_kcal),
            protein=MacroProgressOut(
                consumed_g=consumed_protein.quantize(Decimal("0.01")),
                target_g=target_protein.quantize(Decimal("0.01")),
                remaining_g=remaining_protein.quantize(Decimal("0.01")),
            ),
            fat=MacroProgressOut(
                consumed_g=consumed_fat.quantize(Decimal("0.01")),
                target_g=target_fat.quantize(Decimal("0.01")),
                remaining_g=remaining_fat.quantize(Decimal("0.01")),
            ),
            carbs=MacroProgressOut(
                consumed_g=consumed_carbs.quantize(Decimal("0.01")),
                target_g=target_carbs.quantize(Decimal("0.01")),
                remaining_g=remaining_carbs.quantize(Decimal("0.01")),
            ),
            completed_meals=len(completed),
            planned_meals=planned_meals,
            skipped_meals=len(skipped),
            next_meal_item_id=next_item.id if next_item else None,
            next_meal_type=next_item.meal_type if next_item else None,
            suggestions=suggestions,
            daily_estimated_cost_amount=daily_cost if day_items else None,
        )

    @staticmethod
    def _build_suggestions(
        *,
        day_items: list[MealPlanItem],
        next_item: MealPlanItem | None,
        remaining_protein: Decimal,
        target_protein: Decimal,
    ) -> list[str]:
        suggestions: list[str] = []
        if not day_items:
            suggestions.append("На сегодня блюд в плане нет")
            return suggestions

        completed_or_skipped = all(
            i.status in {"completed", "skipped"} or i.is_completed for i in day_items
        )
        if completed_or_skipped and next_item is None:
            suggestions.append("Все блюда на сегодня выполнены")
            return suggestions

        if next_item is not None:
            label = _MEAL_TYPE_RU.get(next_item.meal_type, next_item.meal_type)
            suggestions.append(f"Следующий приём — {label}")

        # Remaining protein still high relative to target → nudge.
        if target_protein > 0 and remaining_protein >= target_protein * Decimal("0.25"):
            suggestions.append(
                f"До цели по белку осталось {remaining_protein.quantize(Decimal('1'))} г"
            )
        elif remaining_protein <= Decimal("10") and remaining_protein > 0:
            suggestions.append("Белок почти по цели")

        return suggestions

    @staticmethod
    def _build_week_summary(
        plan: MealPlan, items: list[MealPlanItem]
    ) -> WeekSummaryOut:
        by_date: dict[date, list[MealPlanItem]] = {}
        for item in items:
            by_date.setdefault(item.planned_date, []).append(item)

        days: list[WeekDayOut] = []
        cursor = plan.start_date
        while cursor <= plan.end_date:
            day_items = by_date.get(cursor, [])
            if plan.status == "draft":
                status: str = "generating"
            elif not day_items:
                status = "missing"
            else:
                status = "planned"
            completed = sum(
                1 for i in day_items if i.status == "completed" or i.is_completed
            )
            calories = sum(i.calories_kcal for i in day_items)
            protein = sum((i.protein_g for i in day_items), Decimal("0"))
            cost = sum((i.estimated_cost_amount for i in day_items), Decimal("0"))
            days.append(
                WeekDayOut(
                    date=cursor,
                    status=status,  # type: ignore[arg-type]
                    calories_kcal=calories,
                    protein_g=protein.quantize(Decimal("0.01")),
                    completed_meals=completed,
                    planned_meals=len(day_items),
                    estimated_cost_amount=cost.quantize(Decimal("0.01"))
                    if day_items
                    else None,
                )
            )
            cursor = cursor + timedelta(days=1)
        return WeekSummaryOut(days=days)

    @staticmethod
    def _display_recipe_name(name: str) -> str:
        """Strip trailing (YYYY-MM-DD) used by legacy fallback titles."""
        import re

        return re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", name).strip() or name

    @staticmethod
    def _item_out(
        item: MealPlanItem,
        recipe: Recipe,
        image: dict[str, object] | None = None,
    ) -> MealPlanItemOut:
        return MealPlanItemOut(
            id=item.id,
            date=item.planned_date,
            meal_type=item.meal_type,
            servings=item.servings,
            sort_order=item.sort_order,
            status=item.status,
            is_completed=item.is_completed,
            nutrition=DailyTargetsOut(
                calories_kcal=item.calories_kcal,
                protein_g=item.protein_g,
                fat_g=item.fat_g,
                carbohydrate_g=item.carbohydrate_g,
            ),
            estimated_cost_amount=item.estimated_cost_amount,
            recipe=MealPlanRecipeSummary(
                id=recipe.id,
                name=MealPlanService._display_recipe_name(recipe.name),
                calories_kcal=recipe.calories_kcal,
                cook_time_minutes=recipe.cook_time_minutes,
                image=image
                or {"status": "pending", "thumbnail_url": None, "url": None},
            ),
        )


# OwnershipDenied is raised by this service for cross-user access.
__all__ = ["MealPlanService"]
