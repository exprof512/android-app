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
        """Look up active catalog entries by canonical key.

        Loads the full active catalog when resolving AI drafts so aliases and
        soft matching in ``RecipeEngine`` can map colloquial names.
        """
        keys = {canonical_key(name) for name in names}
        keys.discard("")
        if not keys:
            return {}
        # Full active catalog: alias/fuzzy resolution needs targets not present
        # in the raw AI name set (e.g. «куриное филе» → «куриная грудка»).
        return await self.active_catalog()

    async def active_catalog(self) -> dict[str, Ingredient]:
        """All active ingredients keyed by ``normalized_name``."""
        statement = select(Ingredient).where(Ingredient.is_active.is_(True))
        return {
            ingredient.normalized_name: ingredient
            for ingredient in (await self._session.execute(statement)).scalars()
        }

    async def active_canonical_names(self) -> list[str]:
        statement = (
            select(Ingredient.canonical_name)
            .where(Ingredient.is_active.is_(True))
            .order_by(Ingredient.canonical_name)
        )
        return list((await self._session.execute(statement)).scalars())

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

    async def list_favorites(self, user_id: UUID) -> list[Recipe]:
        statement = (
            select(Recipe)
            .join(
                UserRecipeFavorite,
                UserRecipeFavorite.recipe_id == Recipe.id,
            )
            .where(
                UserRecipeFavorite.user_id == user_id,
                Recipe.status == "ready",
            )
            .order_by(UserRecipeFavorite.created_at.desc())
        )
        return list((await self._session.execute(statement)).scalars())

    async def search_ready(
        self,
        *,
        q: str | None = None,
        max_kcal: int | None = None,
        min_protein_g: float | None = None,
        max_cook_time: int | None = None,
        max_cost: float | None = None,
        limit: int = 50,
    ) -> list[Recipe]:
        statement = select(Recipe).where(Recipe.status == "ready")
        if q:
            statement = statement.where(Recipe.name.ilike(f"%{q.strip()}%"))
        if max_kcal is not None:
            statement = statement.where(Recipe.calories_kcal <= max_kcal)
        if min_protein_g is not None:
            statement = statement.where(Recipe.protein_g >= min_protein_g)
        if max_cook_time is not None:
            statement = statement.where(Recipe.cook_time_minutes <= max_cook_time)
        if max_cost is not None:
            statement = statement.where(Recipe.estimated_cost_amount <= max_cost)
        statement = statement.order_by(Recipe.name.asc()).limit(limit)
        return list((await self._session.execute(statement)).scalars())

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
