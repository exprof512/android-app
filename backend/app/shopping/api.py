"""Shopping list HTTP endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser
from app.shopping.dependencies import get_shopping_service
from app.shopping.schemas import (
    ShoppingGenerateRequest,
    ShoppingListItemOut,
    ShoppingListOut,
)
from app.shopping.service import ShoppingService

router = APIRouter(tags=["shopping"])


@router.post(
    "/shopping-lists/generate",
    response_model=ShoppingListOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_shopping_list(
    payload: ShoppingGenerateRequest,
    user: CurrentUser,
    service: ShoppingService = Depends(get_shopping_service),
) -> ShoppingListOut:
    return await service.generate(user.id, payload)


@router.get("/shopping-lists/current", response_model=ShoppingListOut)
async def current_shopping_list(
    user: CurrentUser,
    meal_plan_id: UUID | None = Query(default=None),
    service: ShoppingService = Depends(get_shopping_service),
) -> ShoppingListOut:
    return await service.current(user.id, meal_plan_id=meal_plan_id)


@router.get("/shopping-lists/{list_id}", response_model=ShoppingListOut)
async def get_shopping_list(
    list_id: str,
    user: CurrentUser,
    service: ShoppingService = Depends(get_shopping_service),
) -> ShoppingListOut:
    return await service.get(user.id, UUID(list_id))


@router.post(
    "/shopping-list-items/{item_id}/complete",
    response_model=ShoppingListItemOut,
)
async def complete_shopping_item(
    item_id: str,
    user: CurrentUser,
    completed: bool = True,
    service: ShoppingService = Depends(get_shopping_service),
) -> ShoppingListItemOut:
    return await service.complete_item(user.id, UUID(item_id), completed=completed)


@router.post(
    "/shopping-list-items/clear-completed",
    response_model=ShoppingListOut,
)
async def clear_completed_shopping_items(
    user: CurrentUser,
    list_id: UUID | None = Query(default=None),
    service: ShoppingService = Depends(get_shopping_service),
) -> ShoppingListOut:
    return await service.clear_completed(user.id, list_id=list_id)
