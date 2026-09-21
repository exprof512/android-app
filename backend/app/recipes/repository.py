"""Persistence for the ingredient catalog, recipes and favorites."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.models import Ingredient, Recipe, UserRecipeFavorite
from app.recipes.normalization import canonical_key


class RecipeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def catalog_for_names(self, names: Iterable[str]) -> dict[str, Ingredient]:
        """Look up active catalog entries by canonical key."""
        keys = {canonical_key(name) for name in names}
        keys.discard("")
        if not keys:
            return {}
        statement = select(Ingredient).where(
            Ingredient.normalized_name.in_(keys), Ingredient.is_active.is_(True)
        )
        return {
            ingredient.normalized_name: ingredient
            for ingredient in (await self._session.execute(statement)).scalars()
        }

    async def get_by_fingerprint(self, fingerprint: str) -> Recipe | None:
        statement = select(Recipe).where(Recipe.recipe_fingerprint == fingerprint)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_recipe(self, recipe_id: UUID) -> Recipe | None:
        return await self._session.get(Recipe, recipe_id)

    async def add_recipe(self, recipe: Recipe) -> Recipe:
        self._session.add(recipe)
        await self._session.flush()
        return recipe

    async def is_favorite(self, user_id: UUID, recipe_id: UUID) -> bool:
        statement = select(UserRecipeFavorite.recipe_id).where(
            UserRecipeFavorite.user_id == user_id,
            UserRecipeFavorite.recipe_id == recipe_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None

    async def add_favorite(self, user_id: UUID, recipe_id: UUID) -> None:
        self._session.add(UserRecipeFavorite(user_id=user_id, recipe_id=recipe_id))
        await self._session.flush()

    async def remove_favorite(self, user_id: UUID, recipe_id: UUID) -> None:
        await self._session.execute(
            delete(UserRecipeFavorite).where(
                UserRecipeFavorite.user_id == user_id,
                UserRecipeFavorite.recipe_id == recipe_id,
            )
        )
        await self._session.flush()

    async def user_has_recipe_in_plans(self, user_id: UUID, recipe_id: UUID) -> bool:
        from app.meal_plans.models import MealPlan, MealPlanItem

        statement = (
            select(MealPlanItem.id)
            .join(MealPlan, MealPlanItem.meal_plan_id == MealPlan.id)
            .where(
                MealPlan.user_id == user_id,
                MealPlanItem.recipe_id == recipe_id,
            )
            .limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None
