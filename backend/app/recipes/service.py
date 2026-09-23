"""RecipeService: persistence, reuse by fingerprint and dish card access."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.recipes.engine import RecipeDraft, RecipeEngine
from app.recipes.errors import RecipeNotFound
from app.recipes.models import Recipe, RecipeIngredient
from app.recipes.repository import RecipeRepository

logger = logging.getLogger(__name__)

REUSED_WARNING = "Рецепт с таким составом уже существует и переиспользован."


@dataclass(frozen=True)
class StoredRecipe:
    recipe: Recipe
    reused: bool
    warnings: list[str]


class RecipeService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: RecipeRepository,
        engine: RecipeEngine,
    ) -> None:
        self._session = session
        self._repository = repository
        self._engine = engine

    async def create_recipe(self, draft: RecipeDraft) -> StoredRecipe:
        catalog = await self._repository.catalog_for_names(
            item.name for item in draft.ingredients
        )
        canonical = self._engine.canonicalize(draft, catalog)

        existing = await self._repository.get_by_fingerprint(canonical.fingerprint)
        if existing is not None:
            return StoredRecipe(
                recipe=existing,
                reused=True,
                warnings=[*canonical.warnings, REUSED_WARNING],
            )

        recipe = Recipe(
            name=canonical.name,
            description=canonical.description,
            recipe_fingerprint=canonical.fingerprint,
            cooking_method=canonical.cooking_method,
            cook_time_minutes=canonical.cook_time_minutes,
            servings=canonical.servings,
            calories_kcal=canonical.nutrition.calories_kcal,
            protein_g=canonical.nutrition.protein_g,
            fat_g=canonical.nutrition.fat_g,
            carbohydrate_g=canonical.nutrition.carbohydrate_g,
            estimated_cost_amount=canonical.estimated_cost_amount,
            currency=canonical.currency,
            steps=canonical.steps,
            status="ready",
            ai_model=canonical.ai_model,
            ingredients=[
                RecipeIngredient(
                    ingredient_id=item.ingredient_id,
                    display_name=item.display_name,
                    quantity_g=item.quantity_g,
                    quantity_value=item.quantity_value,
                    unit=item.unit,
                    cost_amount=item.cost_amount,
                    sort_order=item.sort_order,
                )
                for item in canonical.ingredients
            ],
        )
        await self._repository.add_recipe(recipe)
        await self._session.commit()
        logger.info("recipe_created", extra={"recipe_id": str(recipe.id)})
        return StoredRecipe(recipe=recipe, reused=False, warnings=canonical.warnings)

    async def dish_card(self, user_id: UUID, recipe_id: UUID) -> tuple[Recipe, bool]:
        recipe = await self._readable_recipe(recipe_id)
        is_favorite = await self._repository.is_favorite(user_id, recipe_id)
        if is_favorite or await self._repository.user_has_recipe_in_plans(
            user_id, recipe_id
        ):
            return recipe, is_favorite
        raise RecipeNotFound()

    async def add_favorite(self, user_id: UUID, recipe_id: UUID) -> None:
        await self._readable_recipe(recipe_id)
        if await self._repository.is_favorite(user_id, recipe_id):
            return
        await self._repository.add_favorite(user_id, recipe_id)
        await self._session.commit()

    async def remove_favorite(self, user_id: UUID, recipe_id: UUID) -> None:
        await self._readable_recipe(recipe_id)
        await self._repository.remove_favorite(user_id, recipe_id)
        await self._session.commit()

    async def list_favorites(self, user_id: UUID) -> list[tuple[Recipe, bool]]:
        recipes = await self._repository.list_favorites(user_id)
        return [(recipe, True) for recipe in recipes]

    async def search(
        self,
        user_id: UUID,
        *,
        q: str | None = None,
        max_kcal: int | None = None,
        min_protein_g: float | None = None,
        max_cook_time: int | None = None,
        max_cost: float | None = None,
        limit: int = 50,
    ) -> list[tuple[Recipe, bool]]:
        recipes = await self._repository.search_ready(
            q=q,
            max_kcal=max_kcal,
            min_protein_g=min_protein_g,
            max_cook_time=max_cook_time,
            max_cost=max_cost,
            limit=limit,
        )
        result: list[tuple[Recipe, bool]] = []
        for recipe in recipes:
            # Prefer recipes the user can open (favorite or in plan); also allow
            # catalog search hits so discovery works for ready recipes.
            is_favorite = await self._repository.is_favorite(user_id, recipe.id)
            result.append((recipe, is_favorite))
        return result

    async def _readable_recipe(self, recipe_id: UUID) -> Recipe:
        recipe = await self._repository.get_recipe(recipe_id)
        if recipe is None or recipe.status != "ready":
            raise RecipeNotFound()
        return recipe
