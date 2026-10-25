"""Phase 20 recommendation / adapt / substitution / variant service."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context import AIContextBuilder
from app.ai.drafts import recipe_candidate_to_draft
from app.ai.errors import TextAIValidationFailed
from app.ai.fallback_plans import build_catalog_food_suggestions
from app.ai.models import AiRecommendationRecord
from app.ai.operations import (
    OP_DAILY_ADAPTATION,
    OP_FOOD_SUGGESTION,
    OP_INGREDIENT_SUBSTITUTION,
    OP_RECIPE_VARIANT,
    PROMPT_VERSION_BY_TEXT_OP,
    food_suggestion as food_suggestion_op,
)
from app.ai.service import TextAIService
from app.ai.validator import AIResponseValidator
from app.ai.versions import AI_CONTEXT_SCHEMA_VERSION
from app.auth.models import IdempotencyKey
from app.core.errors import ApiError, OwnershipDenied
from app.core.models import as_utc, utcnow
from app.entitlements import constants as entitlement_constants
from app.entitlements.service import EntitlementsService
from app.meal_plans.models import MealPlan, MealPlanItem
from app.nutrition.diary import NutritionDiaryService
from app.nutrition.engine import NutritionEngine
from app.profiles.models import FoodPreference
from app.profiles.normalization import normalize_food_name
from app.recipes.models import Recipe
from app.recipes.repository import RecipeRepository
from app.recipes.service import RecipeService

logger = logging.getLogger(__name__)

VariantType = Literal["high_protein", "budget", "quick", "pantry"]


class RecommendationCandidateOut(BaseModel):
    name: str
    reason: str | None = None
    tags: list[str] = Field(default_factory=list)
    cook_time_minutes: int
    servings: int
    calories_kcal: int
    protein_g: float
    fat_g: float
    carbohydrate_g: float
    estimated_cost_amount: float | None = None
    currency: str = "RUB"
    recipe_id: UUID | None = None
    warnings: list[str] = Field(default_factory=list)


class RecommendationsOut(BaseModel):
    recommendation_id: UUID
    operation: str
    candidates: list[RecommendationCandidateOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejected_error_codes: list[str] = Field(default_factory=list)


class AdaptDayOut(BaseModel):
    recommendation_id: UUID
    on_date: date
    replacements: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rationale: str | None = None
    note: str = "Предложения не применены. Вызовите apply/execute для подтверждения."


class SubstitutionOut(BaseModel):
    recommendation_id: UUID
    original_name: str
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VariantOut(BaseModel):
    recommendation_id: UUID
    variant: str
    candidate: RecommendationCandidateOut | None = None
    changes_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ActionExecuteOut(BaseModel):
    action_type: str
    status: str
    recommendation_id: UUID | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class RecommendationNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="recommendation_not_found",
            message="Рекомендация не найдена.",
        )


class RecommendationApplyRequired(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="confirmation_required",
            message="Сначала получите предложение, затем явно примените его.",
        )


class RecommendationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        text_ai: TextAIService,
        nutrition: NutritionEngine,
        recipes: RecipeService,
        entitlements: EntitlementsService | None = None,
        settings: Any = None,
        ai_model: str = "mock-text-model",
    ) -> None:
        self._session = session
        self._text_ai = text_ai
        self._nutrition = nutrition
        self._recipes = recipes
        self._entitlements = entitlements
        self._settings = settings
        self._ai_model = ai_model
        self._validator = AIResponseValidator(nutrition)
        self._context = AIContextBuilder(session, settings=settings)

    async def recommend(
        self,
        user_id: UUID,
        *,
        intent: str | None = None,
        meal_type: str | None = None,
        on_date: date | None = None,
    ) -> RecommendationsOut:
        await self._consume_recommendation_quota(user_id)
        from app.core.user_time import local_today_for_user

        day = on_date or await local_today_for_user(self._session, user_id)
        context = await self._context.build(
            user_id,
            intent=intent or "food_suggestion",
            on_date=day,
            extra={
                "meal_type": meal_type,
                "prompt_version": PROMPT_VERSION_BY_TEXT_OP[OP_FOOD_SUGGESTION],
            },
        )
        record = await self._new_record(
            user_id,
            operation=food_suggestion_op.key,
            prompt_version=PROMPT_VERSION_BY_TEXT_OP[OP_FOOD_SUGGESTION],
            context_version=str(context.get("context_version")),
        )
        try:
            response = await self._text_ai.food_suggestion(
                context=context, user_id=user_id, use_cache=True
            )
        except Exception as exc:
            record.status = "failed"
            record.error_code = getattr(exc, "code", "ai_unavailable")
            await self._session.commit()
            raise

        catalog = await RecipeRepository(self._session).active_catalog()
        candidates_out: list[RecommendationCandidateOut] = []
        rejected: list[str] = []
        warnings: list[str] = []
        first_recipe_id: UUID | None = None

        for item in response.candidates:
            validated = self._validator.validate_from_context(
                item.recipe, catalog=catalog, context=context
            )
            if not validated.ok or validated.canonical is None:
                rejected.extend(validated.error_codes)
                continue
            source = validated.repaired_candidate or item.recipe
            stored = await self._recipes.create_recipe(
                recipe_candidate_to_draft(source, ai_model=self._ai_model)
            )
            recipe = stored.recipe
            if first_recipe_id is None:
                first_recipe_id = recipe.id
            candidates_out.append(
                self._candidate_out(
                    recipe,
                    reason=item.reason,
                    tags=list(item.tags),
                    warnings=validated.warnings + stored.warnings,
                )
            )
            warnings.extend(validated.warnings)

        if not candidates_out:
            await self._text_ai.invalidate_cache(
                operation="food_suggestion", context=context
            )
            logger.info(
                "food_suggestion_domain_fallback",
                extra={
                    "error_code": rejected[0] if rejected else "no_valid_candidates",
                    "rejected_count": len(rejected),
                },
            )
            fallback = await self._persist_catalog_suggestions(
                catalog_count=3,
                reason="Подобрано из каталога: AI-кандидаты не прошли проверку.",
                tags=["fallback"],
            )
            if fallback:
                candidates_out, first_recipe_id, fb_warnings = fallback
                warnings.extend(fb_warnings)
                warnings.append("ai_candidates_catalog_fallback")
            else:
                record.status = "failed"
                record.error_code = rejected[0] if rejected else "no_valid_candidates"
                await self._session.commit()
                raise TextAIValidationFailed(
                    details=[{"field": "candidates", "reason": record.error_code}]
                )

        record.status = "proposed"
        record.recipe_id = first_recipe_id
        await self._session.commit()
        return RecommendationsOut(
            recommendation_id=record.id,
            operation=food_suggestion_op.key,
            candidates=candidates_out,
            warnings=list(dict.fromkeys(warnings)),
            rejected_error_codes=list(dict.fromkeys(rejected)),
        )

    async def adapt_day(
        self, user_id: UUID, *, on_date: date | None = None
    ) -> AdaptDayOut:
        await self._consume_recommendation_quota(user_id)
        from app.core.user_time import local_today_for_user

        day = on_date or await local_today_for_user(self._session, user_id)
        context = await self._context.build(
            user_id,
            intent="adapt_day",
            on_date=day,
            extra={
                "prompt_version": PROMPT_VERSION_BY_TEXT_OP[OP_DAILY_ADAPTATION],
            },
        )
        remaining = [
            m["meal_type"]
            for m in (context.get("plan_meals") or [])
            if not m.get("is_completed")
        ]
        context["remaining_meal_types"] = remaining

        record = await self._new_record(
            user_id,
            operation="daily_adaptation",
            prompt_version=PROMPT_VERSION_BY_TEXT_OP[OP_DAILY_ADAPTATION],
            context_version=str(context.get("context_version")),
        )
        if not remaining:
            record.status = "proposed"
            await self._session.commit()
            return AdaptDayOut(
                recommendation_id=record.id,
                on_date=day,
                replacements=[],
                warnings=["Нет незавершённых приёмов пищи на эту дату."],
            )

        try:
            response = await self._text_ai.daily_adaptation(
                context=context, user_id=user_id, use_cache=False
            )
        except Exception as exc:
            record.status = "failed"
            record.error_code = getattr(exc, "code", "ai_unavailable")
            await self._session.commit()
            raise

        catalog = await RecipeRepository(self._session).active_catalog()
        replacements: list[dict[str, Any]] = []
        warnings: list[str] = []
        for slot in response.replacements:
            if slot.meal_type not in remaining:
                continue
            validated = self._validator.validate_from_context(
                slot.recipe, catalog=catalog, context=context
            )
            if not validated.ok or validated.canonical is None:
                warnings.extend(validated.error_codes)
                continue
            source = validated.repaired_candidate or slot.recipe
            stored = await self._recipes.create_recipe(
                recipe_candidate_to_draft(source, ai_model=self._ai_model)
            )
            out = self._candidate_out(
                stored.recipe,
                reason=slot.reason,
                tags=[],
                warnings=validated.warnings + stored.warnings,
            )
            replacements.append(
                {
                    "meal_type": slot.meal_type,
                    "reason": slot.reason,
                    "candidate": out.model_dump(mode="json"),
                }
            )

        record.status = "proposed"
        await self._session.commit()
        return AdaptDayOut(
            recommendation_id=record.id,
            on_date=day,
            replacements=replacements,
            warnings=list(dict.fromkeys(warnings)),
            rationale=response.rationale,
        )

    async def ingredient_substitution(
        self,
        user_id: UUID,
        *,
        recipe_id: UUID,
        ingredient_name: str,
    ) -> SubstitutionOut:
        await self._consume_recommendation_quota(user_id)
        recipe = await self._session.get(Recipe, recipe_id)
        if recipe is None:
            raise ApiError(
                status_code=404,
                code="recipe_not_found",
                message="Рецепт не найден.",
            )
        context = await self._context.build(
            user_id,
            intent="ingredient_substitution",
            recipe_id=recipe_id,
            extra={
                "ingredient_name": ingredient_name,
                "recipe_name": recipe.name,
                "prompt_version": PROMPT_VERSION_BY_TEXT_OP[
                    OP_INGREDIENT_SUBSTITUTION
                ],
            },
        )
        record = await self._new_record(
            user_id,
            operation="ingredient_substitution",
            prompt_version=PROMPT_VERSION_BY_TEXT_OP[OP_INGREDIENT_SUBSTITUTION],
            context_version=str(context.get("context_version")),
            recipe_id=recipe_id,
        )
        try:
            response = await self._text_ai.ingredient_substitution(
                context=context, user_id=user_id, use_cache=False
            )
        except Exception as exc:
            record.status = "failed"
            record.error_code = getattr(exc, "code", "ai_unavailable")
            await self._session.commit()
            raise

        allowed = set(context.get("allowed_ingredients") or [])
        restricted = {
            normalize_food_name(n) for n in (context.get("restrictions") or [])
        }
        alternatives: list[dict[str, Any]] = []
        warnings: list[str] = []
        for alt in response.alternatives:
            key = normalize_food_name(alt.name)
            if allowed and not any(
                normalize_food_name(a) == key for a in allowed
            ):
                warnings.append("unknown_ingredient")
                continue
            if key in restricted:
                warnings.append("allergy_or_restriction")
                continue
            alternatives.append(
                {
                    "name": alt.name,
                    "quantity": alt.quantity,
                    "unit": alt.unit,
                    "reason": alt.reason,
                }
            )

        record.status = "proposed"
        await self._session.commit()
        return SubstitutionOut(
            recommendation_id=record.id,
            original_name=response.original_name or ingredient_name,
            alternatives=alternatives,
            warnings=list(dict.fromkeys(warnings)),
        )

    async def recipe_variant(
        self,
        user_id: UUID,
        *,
        recipe_id: UUID,
        variant: VariantType,
    ) -> VariantOut:
        await self._consume_recommendation_quota(user_id)
        recipe = await self._session.get(Recipe, recipe_id)
        if recipe is None:
            raise ApiError(
                status_code=404,
                code="recipe_not_found",
                message="Рецепт не найден.",
            )
        context = await self._context.build(
            user_id,
            intent=f"recipe_variant:{variant}",
            recipe_id=recipe_id,
            extra={
                "variant": variant,
                "base_recipe_name": recipe.name,
                "prompt_version": PROMPT_VERSION_BY_TEXT_OP[OP_RECIPE_VARIANT],
            },
        )
        record = await self._new_record(
            user_id,
            operation="recipe_variant",
            prompt_version=PROMPT_VERSION_BY_TEXT_OP[OP_RECIPE_VARIANT],
            context_version=str(context.get("context_version")),
            recipe_id=recipe_id,
        )
        try:
            response = await self._text_ai.recipe_variant(
                context=context, user_id=user_id, use_cache=True
            )
        except Exception as exc:
            record.status = "failed"
            record.error_code = getattr(exc, "code", "ai_unavailable")
            await self._session.commit()
            raise

        catalog = await RecipeRepository(self._session).active_catalog()
        validated = self._validator.validate_from_context(
            response.recipe, catalog=catalog, context=context
        )
        if not validated.ok or validated.canonical is None:
            record.status = "failed"
            record.error_code = (
                validated.error_codes[0] if validated.error_codes else "invalid"
            )
            await self._session.commit()
            raise TextAIValidationFailed(
                details=[
                    {"field": "recipe", "reason": c} for c in validated.error_codes
                ]
            )

        stored = await self._recipes.create_recipe(
            recipe_candidate_to_draft(
                validated.repaired_candidate or response.recipe,
                ai_model=self._ai_model,
            )
        )
        record.status = "proposed"
        record.recipe_id = stored.recipe.id
        await self._session.commit()
        return VariantOut(
            recommendation_id=record.id,
            variant=response.variant,
            candidate=self._candidate_out(
                stored.recipe,
                reason=response.changes_summary,
                tags=[response.variant],
                warnings=validated.warnings + stored.warnings,
            ),
            changes_summary=response.changes_summary,
            warnings=validated.warnings + stored.warnings,
        )

    async def apply(
        self,
        user_id: UUID,
        recommendation_id: UUID,
        *,
        action_type: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ActionExecuteOut:
        return await self.execute(
            user_id,
            action_type=action_type,
            payload=payload or {},
            recommendation_id=recommendation_id,
            idempotency_key=idempotency_key,
        )

    async def execute(
        self,
        user_id: UUID,
        *,
        action_type: str,
        payload: dict[str, Any],
        recommendation_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ActionExecuteOut:
        if idempotency_key:
            cached = await self._load_idempotent(user_id, idempotency_key)
            if cached is not None:
                return cached

        record: AiRecommendationRecord | None = None
        if recommendation_id is not None:
            record = await self._session.get(AiRecommendationRecord, recommendation_id)
            if record is None or record.user_id != user_id:
                raise RecommendationNotFound()
            if record.status not in {"proposed", "selected"}:
                raise RecommendationApplyRequired()

        # Mutations require an explicit recommendation_id (two-step confirm).
        mutating = action_type in {
            "replace_meal_item",
            "create_nutrition_log",
            "remember_dislike",
        }
        if mutating and recommendation_id is None:
            raise RecommendationApplyRequired()

        result: dict[str, Any] = {}
        if action_type == "replace_meal_item":
            result = await self._apply_replace(user_id, payload, record)
        elif action_type == "create_nutrition_log":
            result = await self._apply_nutrition_log(user_id, payload, record)
        elif action_type == "remember_dislike":
            result = await self._apply_dislike(user_id, payload, record)
        elif action_type in {
            "open_shopping_list",
            "explain_balance",
            "food_suggestion",
            "adapt_day",
            "make_cheaper",
            "make_faster",
            "more_protein",
            "pantry_cook",
            "none",
        }:
            result = {"acknowledged": True}
        else:
            raise ApiError(
                status_code=400,
                code="unknown_action_type",
                message=f"Неизвестный action_type: {action_type}",
            )

        if record is not None and mutating:
            record.status = "selected"

        out = ActionExecuteOut(
            action_type=action_type,
            status="applied",
            recommendation_id=recommendation_id,
            result=result,
        )
        # Persist the mutation and its idempotency record in one transaction,
        # otherwise a retry after a crash re-applies the action.
        if idempotency_key:
            await self._store_idempotent(user_id, idempotency_key, out)
        await self._session.commit()
        return out

    async def _apply_replace(
        self,
        user_id: UUID,
        payload: dict[str, Any],
        record: AiRecommendationRecord | None,
    ) -> dict[str, Any]:
        item_id_raw = payload.get("meal_plan_item_id")
        recipe_id_raw = payload.get("recipe_id") or (
            str(record.recipe_id) if record and record.recipe_id else None
        )
        if not item_id_raw or not recipe_id_raw:
            raise ApiError(
                status_code=400,
                code="invalid_payload",
                message="Нужны meal_plan_item_id и recipe_id.",
            )
        item_id = UUID(str(item_id_raw))
        recipe_id = UUID(str(recipe_id_raw))
        item = await self._session.get(MealPlanItem, item_id)
        if item is None:
            raise ApiError(
                status_code=404,
                code="meal_plan_item_not_found",
                message="Слот плана не найден.",
            )
        plan = await self._session.get(MealPlan, item.meal_plan_id)
        if plan is None or plan.user_id != user_id:
            raise OwnershipDenied()
        recipe = await self._session.get(Recipe, recipe_id)
        if recipe is None:
            raise ApiError(
                status_code=404,
                code="recipe_not_found",
                message="Рецепт не найден.",
            )
        if self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_MEAL_REPLACE
            )
        servings = item.servings
        item.recipe_id = recipe.id
        item.status = "replaced"
        item.calories_kcal = int(round(recipe.calories_kcal * float(servings)))
        item.protein_g = (recipe.protein_g * servings).quantize(Decimal("0.01"))
        item.fat_g = (recipe.fat_g * servings).quantize(Decimal("0.01"))
        item.carbohydrate_g = (recipe.carbohydrate_g * servings).quantize(
            Decimal("0.01")
        )
        if recipe.estimated_cost_amount is not None:
            item.estimated_cost_amount = (
                recipe.estimated_cost_amount * servings
            ).quantize(Decimal("0.01"))
        if record is not None:
            record.recipe_id = recipe.id
        await self._session.flush()
        return {
            "meal_plan_item_id": str(item.id),
            "recipe_id": str(recipe.id),
            "recipe_name": recipe.name,
        }

    async def _apply_nutrition_log(
        self,
        user_id: UUID,
        payload: dict[str, Any],
        record: AiRecommendationRecord | None,
    ) -> dict[str, Any]:
        recipe_id_raw = payload.get("recipe_id") or (
            str(record.recipe_id) if record and record.recipe_id else None
        )
        if not recipe_id_raw:
            raise ApiError(
                status_code=400,
                code="invalid_payload",
                message="Нужен recipe_id.",
            )
        recipe_id = UUID(str(recipe_id_raw))
        meal_type = str(payload.get("meal_type") or "snack")
        from app.core.user_time import local_today_for_user

        logged_on = date.fromisoformat(
            str(
                payload.get("date")
                or (await local_today_for_user(self._session, user_id)).isoformat()
            )
        )
        servings = Decimal(str(payload.get("servings") or 1))
        row = await NutritionDiaryService(self._session).create(
            user_id,
            logged_on=logged_on,
            meal_type=meal_type,
            source="recipe",
            recipe_id=recipe_id,
            servings=servings,
        )
        return {"nutrition_log_id": str(row.id), "calories_kcal": row.calories_kcal}

    async def _apply_dislike(
        self,
        user_id: UUID,
        payload: dict[str, Any],
        record: AiRecommendationRecord | None,
    ) -> dict[str, Any]:
        del record  # audit only via caller
        name = str(payload.get("name") or payload.get("food_name") or "").strip()
        if not name:
            raise ApiError(
                status_code=400,
                code="invalid_payload",
                message="Нужно name для remember_dislike.",
            )
        normalized = normalize_food_name(name)
        existing = (
            await self._session.execute(
                select(FoodPreference).where(
                    FoodPreference.user_id == user_id,
                    FoodPreference.normalized_food_name == normalized,
                    FoodPreference.preference_type == "disliked",
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self._session.add(
                FoodPreference(
                    user_id=user_id,
                    display_name=name[:255],
                    normalized_food_name=normalized,
                    preference_type="disliked",
                )
            )
            await self._session.flush()
        return {"disliked": name}

    async def _persist_catalog_suggestions(
        self,
        *,
        catalog_count: int,
        reason: str,
        tags: list[str],
    ) -> tuple[list[RecommendationCandidateOut], UUID | None, list[str]] | None:
        recipes = await build_catalog_food_suggestions(
            self._session, count=catalog_count
        )
        if not recipes:
            return None
        out: list[RecommendationCandidateOut] = []
        warnings: list[str] = []
        first_id: UUID | None = None
        for recipe_candidate in recipes:
            stored = await self._recipes.create_recipe(
                recipe_candidate_to_draft(recipe_candidate, ai_model="catalog-fallback")
            )
            if first_id is None:
                first_id = stored.recipe.id
            out.append(
                self._candidate_out(
                    stored.recipe,
                    reason=reason,
                    tags=tags,
                    warnings=stored.warnings,
                )
            )
            warnings.extend(stored.warnings)
        return out, first_id, warnings

    async def _consume_recommendation_quota(self, user_id: UUID) -> None:
        if self._entitlements is not None:
            await self._entitlements.consume(
                user_id, entitlement_constants.FEATURE_AI_RECOMMENDATION
            )

    async def _new_record(
        self,
        user_id: UUID,
        *,
        operation: str,
        prompt_version: str | None,
        context_version: str | None = AI_CONTEXT_SCHEMA_VERSION,
        recipe_id: UUID | None = None,
    ) -> AiRecommendationRecord:
        record = AiRecommendationRecord(
            user_id=user_id,
            operation=operation,
            status="proposed",
            context_version=context_version,
            prompt_version=prompt_version,
            model=self._ai_model,
            recipe_id=recipe_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    @staticmethod
    def _candidate_out(
        recipe: Recipe,
        *,
        reason: str | None,
        tags: list[str],
        warnings: list[str],
    ) -> RecommendationCandidateOut:
        return RecommendationCandidateOut(
            name=recipe.name,
            reason=reason,
            tags=tags,
            cook_time_minutes=recipe.cook_time_minutes,
            servings=recipe.servings,
            calories_kcal=recipe.calories_kcal,
            protein_g=float(recipe.protein_g),
            fat_g=float(recipe.fat_g),
            carbohydrate_g=float(recipe.carbohydrate_g),
            estimated_cost_amount=(
                float(recipe.estimated_cost_amount)
                if recipe.estimated_cost_amount is not None
                else None
            ),
            currency=recipe.currency or "RUB",
            recipe_id=recipe.id,
            warnings=warnings,
        )

    async def _load_idempotent(
        self, user_id: UUID, key: str
    ) -> ActionExecuteOut | None:
        row = (
            await self._session.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.user_id == user_id,
                    IdempotencyKey.endpoint == "ai_action_execute",
                    IdempotencyKey.key == key,
                )
            )
        ).scalar_one_or_none()
        if row is None or as_utc(row.expires_at) <= utcnow():
            return None
        if row.response_body:
            return ActionExecuteOut.model_validate(row.response_body)
        return None

    async def _store_idempotent(
        self, user_id: UUID, key: str, out: ActionExecuteOut
    ) -> None:
        existing = await self._load_idempotent(user_id, key)
        if existing is not None:
            return
        body = out.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        self._session.add(
            IdempotencyKey(
                user_id=user_id,
                key=key[:255],
                endpoint="ai_action_execute",
                request_hash=digest,
                response_status=200,
                response_body=body,
                expires_at=utcnow() + timedelta(hours=24),
            )
        )
        await self._session.flush()
