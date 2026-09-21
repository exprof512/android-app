"""Recipe dependency wiring."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_services
from app.core.services import Services
from app.recipes.engine import RecipeEngine
from app.recipes.repository import RecipeRepository
from app.recipes.service import RecipeService


def get_recipe_service(
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
) -> RecipeService:
    return RecipeService(
        session=session,
        repository=RecipeRepository(session),
        engine=RecipeEngine(services.nutrition),
    )
