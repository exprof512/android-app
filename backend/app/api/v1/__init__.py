"""Versioned HTTP layer for the FoodAI API."""

from fastapi import APIRouter

from app.admin.ai_api import router as admin_ai_router
from app.analytics.api import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recipes import router as recipes_router
from app.api.v1.users import router as users_router
from app.chat.api import router as chat_router
from app.entitlements.api import router as entitlements_router
from app.images.api import router as images_router
from app.meal_plans.api import router as meal_plans_router
from app.nutrition.api import router as nutrition_router
from app.progress.api import router as progress_router
from app.shopping.api import router as shopping_router
from app.water.api import router as water_router


def create_api_router(prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix)
    router.include_router(auth_router)
    router.include_router(users_router)
    router.include_router(profile_router)
    router.include_router(recipes_router)
    router.include_router(meal_plans_router)
    router.include_router(images_router)
    router.include_router(shopping_router)
    router.include_router(progress_router)
    router.include_router(chat_router)
    router.include_router(entitlements_router)
    router.include_router(nutrition_router)
    router.include_router(analytics_router)
    router.include_router(admin_ai_router)
    router.include_router(water_router)
    return router


__all__ = ["create_api_router"]
