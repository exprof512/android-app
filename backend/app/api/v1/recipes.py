"""Recipe dish card and favorite endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.auth.dependencies import CurrentUser
from app.recipes.dependencies import get_recipe_service
from app.recipes.models import Recipe
from app.recipes.schemas import (
    DishCardCost,
    DishCardIngredient,
    DishCardNutrition,
    DishCardResponse,
)
from app.recipes.service import RecipeService

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _dish_card(recipe: Recipe, *, is_favorite: bool) -> DishCardResponse:
    return DishCardResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        cooking_method=recipe.cooking_method,
        cook_time_minutes=recipe.cook_time_minutes,
        servings=recipe.servings,
        status=recipe.status,
        nutrition_per_serving=DishCardNutrition(
            calories_kcal=recipe.calories_kcal,
            protein_g=recipe.protein_g,
            fat_g=recipe.fat_g,
            carbohydrate_g=recipe.carbohydrate_g,
        ),
        estimated_cost_per_serving=DishCardCost(
            amount=recipe.estimated_cost_amount, currency=recipe.currency
        ),
        ingredients=[
            DishCardIngredient(
                name=item.display_name,
                grams=item.quantity_g,
                quantity=item.quantity_value,
                unit=item.unit,
                cost=item.cost_amount,
            )
            for item in recipe.ingredients
        ],
        steps=list(recipe.steps),
        is_favorite=is_favorite,
    )


@router.get("/{recipe_id}", response_model=DishCardResponse)
async def read_recipe(
    recipe_id: UUID,
    current_user: CurrentUser,
    recipe_service: RecipeService = Depends(get_recipe_service),
) -> DishCardResponse:
    recipe, is_favorite = await recipe_service.dish_card(current_user.id, recipe_id)
    return _dish_card(recipe, is_favorite=is_favorite)


@router.post("/{recipe_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(
    recipe_id: UUID,
    current_user: CurrentUser,
    recipe_service: RecipeService = Depends(get_recipe_service),
) -> Response:
    await recipe_service.add_favorite(current_user.id, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{recipe_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    recipe_id: UUID,
    current_user: CurrentUser,
    recipe_service: RecipeService = Depends(get_recipe_service),
) -> Response:
    await recipe_service.remove_favorite(current_user.id, recipe_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
