"""Recipe dish card and favorite endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

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


@router.get("/favorites", response_model=list[DishCardResponse])
async def list_favorite_recipes(
    current_user: CurrentUser,
    recipe_service: RecipeService = Depends(get_recipe_service),
) -> list[DishCardResponse]:
    rows = await recipe_service.list_favorites(current_user.id)
    return [_dish_card(recipe, is_favorite=fav) for recipe, fav in rows]


@router.get("/search", response_model=list[DishCardResponse])
async def search_recipes(
    current_user: CurrentUser,
    q: str | None = Query(default=None),
    max_kcal: int | None = Query(default=None, ge=1),
    min_protein_g: float | None = Query(default=None, ge=0),
    max_cook_time: int | None = Query(default=None, ge=1),
    max_cost: float | None = Query(default=None, ge=0),
    recipe_service: RecipeService = Depends(get_recipe_service),
) -> list[DishCardResponse]:
    rows = await recipe_service.search(
        current_user.id,
        q=q,
        max_kcal=max_kcal,
        min_protein_g=min_protein_g,
        max_cook_time=max_cook_time,
        max_cost=max_cost,
    )
    return [_dish_card(recipe, is_favorite=fav) for recipe, fav in rows]


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
