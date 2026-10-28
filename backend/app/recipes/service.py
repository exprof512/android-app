"""RecipeService: persistence, reuse by fingerprint and dish card access."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.meal_plans.models import MealPlan, MealPlanItem
from app.recipes.engine import RecipeDraft, RecipeEngine
from app.recipes.errors import RecipeNotFound, RecipeValidationError
from app.recipes.fingerprint import recipe_fingerprint
from app.recipes.errors import RecipeNotFound
from app.recipes.models import Recipe, RecipeIngredient, UserRecipeFavorite
from app.recipes.schemas import IngredientSubstitutionApplyRequest
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

    async def apply_substitution(
        self,
        user_id: UUID,
        recipe_id: UUID,
        payload: IngredientSubstitutionApplyRequest,
    ) -> Recipe:
        in_plans = await self._repository.user_has_recipe_in_plans(user_id, recipe_id)
        favorite = await self._repository.is_favorite(user_id, recipe_id)
        if not (in_plans or favorite):
            raise RecipeNotFound()

        source = await self._repository.get_recipe(recipe_id)
        if source is None:
            raise RecipeNotFound()
        target = next(
            (
                item
                for item in source.ingredients
                if item.display_name.strip().lower() == payload.original_name.strip().lower()
            ),
            None,
        )
        if target is None:
            raise RecipeValidationError(
                [{"field": "original_name", "reason": "not_found"}]
            )

        catalog = await self._repository.active_catalog()
        replacement = next(
            (
                item
                for item in catalog.values()
                if item.canonical_name.strip().lower()
                == payload.replacement_name.strip().lower()
                or item.normalized_name == payload.replacement_name.strip().lower()
            ),
            None,
        )
        if replacement is None:
            raise RecipeValidationError(
                [{"field": "replacement_name", "reason": "not_found"}]
            )

        quantity_g = (
            Decimal(str(payload.quantity_g))
            if payload.quantity_g is not None
            else target.quantity_g
        )
        by_name = {item.canonical_name.strip().lower(): item for item in catalog.values()}
        calories = Decimal("0")
        protein = Decimal("0")
        fat = Decimal("0")
        carbs = Decimal("0")
        cost = Decimal("0")
        rows: list[RecipeIngredient] = []
        for item in source.ingredients:
            name = (
                replacement.canonical_name
                if item.id == target.id
                else item.display_name
            )
            grams = quantity_g if item.id == target.id else item.quantity_g
            catalog_item = replacement if item.id == target.id else by_name.get(
                item.display_name.strip().lower()
            )
            ingredients_copy = RecipeIngredient(
                ingredient_id=replacement.id if item.id == target.id else item.ingredient_id,
                display_name=name,
                quantity_g=grams,
                quantity_value=quantity_g if item.id == target.id else item.quantity_value,
                unit="g" if item.id == target.id else item.unit,
                cost_amount=(
                    replacement.reference_price_per_100g * grams / Decimal("100")
                    if item.id == target.id
                    and replacement.reference_price_per_100g is not None
                    else (item.cost_amount if item.id != target.id else None)
                ),
                sort_order=item.sort_order,
            )
            rows.append(ingredients_copy)
            if catalog_item is not None:
                factor = grams / Decimal("100")
                calories += catalog_item.calories_per_100g * factor
                protein += catalog_item.protein_per_100g * factor
                fat += catalog_item.fat_per_100g * factor
                carbs += catalog_item.carbohydrate_per_100g * factor
            if ingredients_copy.cost_amount is not None:
                cost += ingredients_copy.cost_amount

        servings = Decimal(source.servings)
        recipe = Recipe(
            created_by_user_id=user_id,
            name=source.name,
            description=source.description,
            recipe_fingerprint=recipe_fingerprint(
                name=source.name,
                cooking_method=source.cooking_method,
                servings=source.servings,
                ingredients=[(row.ingredient_id, row.quantity_g) for row in rows],
            ),
            cooking_method=source.cooking_method,
            cook_time_minutes=source.cook_time_minutes,
            servings=source.servings,
            calories_kcal=int((calories / servings).to_integral_value()),
            protein_g=(protein / servings).quantize(Decimal("0.01")),
            fat_g=(fat / servings).quantize(Decimal("0.01")),
            carbohydrate_g=(carbs / servings).quantize(Decimal("0.01")),
            estimated_cost_amount=(cost / servings).quantize(Decimal("0.01")),
            currency=source.currency,
            steps=list(source.steps),
            status="ready",
            ai_model=source.ai_model,
            ingredients=rows,
        )
        self._session.add(recipe)
        await self._session.flush()

        plan_ids = select(MealPlan.id).where(MealPlan.user_id == user_id)
        await self._session.execute(
            update(MealPlanItem)
            .where(
                MealPlanItem.recipe_id == recipe_id,
                MealPlanItem.meal_plan_id.in_(plan_ids),
            )
            .values(recipe_id=recipe.id)
        )
        await self._session.execute(
            update(UserRecipeFavorite)
            .where(
                UserRecipeFavorite.user_id == user_id,
                UserRecipeFavorite.recipe_id == recipe_id,
            )
            .values(recipe_id=recipe.id)
        )
        await self._session.commit()
        await self._session.refresh(recipe)
        logger.info("recipe_substituted", extra={"recipe_id": str(recipe.id)})
        return recipe

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
