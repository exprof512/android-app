"""Phase 20 Adaptive AI HTTP endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_text_ai_service
from app.ai.recommendations import (
    ActionExecuteOut,
    AdaptDayOut,
    RecommendationService,
    RecommendationsOut,
    SubstitutionOut,
    VariantOut,
)
from app.ai.service import TextAIService
from app.auth.dependencies import CurrentUser
from app.core.dependencies import get_db_session, get_services
from app.core.services import Services
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService
from app.recipes.dependencies import get_recipe_service
from app.recipes.service import RecipeService

router = APIRouter(prefix="/ai", tags=["ai"])


class RecommendRequest(BaseModel):
    intent: str | None = None
    meal_type: str | None = None
    on_date: date | None = Field(default=None, alias="date")

    model_config = {"populate_by_name": True}


class AdaptDayRequest(BaseModel):
    on_date: date | None = Field(default=None, alias="date")

    model_config = {"populate_by_name": True}


class SubstitutionRequest(BaseModel):
    recipe_id: UUID
    ingredient_name: str = Field(min_length=1, max_length=255)


class VariantRequest(BaseModel):
    recipe_id: UUID
    variant: Literal["high_protein", "budget", "quick", "pantry"]


class ApplyRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    recommendation_id: UUID | None = None


def get_recommendation_service(
    session: AsyncSession = Depends(get_db_session),
    text_ai: TextAIService = Depends(get_text_ai_service),
    recipes: RecipeService = Depends(get_recipe_service),
    entitlements: EntitlementsService = Depends(get_entitlements_service),
    services: Services = Depends(get_services),
) -> RecommendationService:
    settings = services.settings
    model_name = (
        settings.openai_text_model
        or settings.deepseek_text_model
        or "mock-text-model"
    )
    return RecommendationService(
        session=session,
        text_ai=text_ai,
        nutrition=services.nutrition,
        recipes=recipes,
        entitlements=entitlements,
        settings=settings,
        ai_model=model_name,
    )


@router.post("/recommendations", response_model=RecommendationsOut)
async def create_recommendations(
    payload: RecommendRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationsOut:
    return await service.recommend(
        user.id,
        intent=payload.intent,
        meal_type=payload.meal_type,
        on_date=payload.on_date,
    )


@router.post("/adapt-day", response_model=AdaptDayOut)
async def adapt_day(
    payload: AdaptDayRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> AdaptDayOut:
    return await service.adapt_day(user.id, on_date=payload.on_date)


@router.post("/ingredient-substitution", response_model=SubstitutionOut)
async def ingredient_substitution(
    payload: SubstitutionRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> SubstitutionOut:
    return await service.ingredient_substitution(
        user.id,
        recipe_id=payload.recipe_id,
        ingredient_name=payload.ingredient_name,
    )


@router.post("/recipe-variant", response_model=VariantOut)
async def recipe_variant(
    payload: VariantRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
) -> VariantOut:
    return await service.recipe_variant(
        user.id, recipe_id=payload.recipe_id, variant=payload.variant
    )


@router.post(
    "/recommendations/{recommendation_id}/apply",
    response_model=ActionExecuteOut,
)
async def apply_recommendation(
    recommendation_id: UUID,
    payload: ApplyRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ActionExecuteOut:
    return await service.apply(
        user.id,
        recommendation_id,
        action_type=payload.action_type,
        payload=payload.payload,
        idempotency_key=idempotency_key,
    )


@router.post("/actions/execute", response_model=ActionExecuteOut)
async def execute_action(
    payload: ExecuteRequest,
    user: CurrentUser,
    service: RecommendationService = Depends(get_recommendation_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ActionExecuteOut:
    return await service.execute(
        user.id,
        action_type=payload.action_type,
        payload=payload.payload,
        recommendation_id=payload.recommendation_id,
        idempotency_key=idempotency_key,
    )
