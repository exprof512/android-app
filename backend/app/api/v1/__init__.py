"""Versioned HTTP layer for the FoodAI API."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recipes import router as recipes_router
from app.api.v1.users import router as users_router
from app.meal_plans.api import router as meal_plans_router


def create_api_router(prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix)
    router.include_router(auth_router)
    router.include_router(users_router)
    router.include_router(profile_router)
    router.include_router(recipes_router)
    router.include_router(meal_plans_router)
    return router


__all__ = ["create_api_router"]
