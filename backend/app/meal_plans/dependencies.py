"""Meal plan dependency wiring."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_text_ai_service
from app.ai.service import TextAIService
from app.core.config import Settings
from app.core.dependencies import get_db_session, get_services
from app.core.services import Services
from app.entitlements.dependencies import get_entitlements_service
from app.entitlements.service import EntitlementsService
from app.images.dependencies import get_image_service
from app.images.service import ImageGenerationService
from app.meal_plans.engine import MealPlanEngine
from app.meal_plans.repository import MealPlanRepository
from app.meal_plans.service import MealPlanService
from app.profiles.dependencies import get_profile_service
from app.profiles.service import ProfileService
from app.recipes.dependencies import get_recipe_service
from app.recipes.engine import RecipeEngine
from app.recipes.service import RecipeService


def get_meal_plan_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
    profile_service: ProfileService = Depends(get_profile_service),
    recipe_service: RecipeService = Depends(get_recipe_service),
    text_ai: TextAIService = Depends(get_text_ai_service),
    image_service: ImageGenerationService = Depends(get_image_service),
    entitlements: EntitlementsService = Depends(get_entitlements_service),
) -> MealPlanService:
    settings: Settings = request.app.state.settings
    return MealPlanService(
        session=session,
        repository=MealPlanRepository(session),
        profile_service=profile_service,
        recipe_service=recipe_service,
        recipe_engine=RecipeEngine(services.nutrition),
        meal_plan_engine=MealPlanEngine(),
        text_ai=text_ai,
        ai_model=settings.deepseek_text_model or "deepseek-chat",
        image_service=image_service,
        entitlements=entitlements,
    )
