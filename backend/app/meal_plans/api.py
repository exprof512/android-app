"""Meal plan HTTP endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.auth.dependencies import CurrentUser
from app.meal_plans.dependencies import get_meal_plan_service
from app.meal_plans.schemas import (
    MealPlanGenerateRequest,
    MealPlanItemOut,
    MealPlanOut,
    MealPlanRegenerateRequest,
    MealPlanReplaceRequest,
)
from app.meal_plans.service import MealPlanService

router = APIRouter(tags=["meal-plans"])


@router.post(
    "/meal-plans/generate",
    response_model=MealPlanOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_meal_plan(
    payload: MealPlanGenerateRequest,
    user: CurrentUser,
    service: MealPlanService = Depends(get_meal_plan_service),
) -> MealPlanOut:
    return await service.generate(user.id, payload)


@router.get("/meal-plans/today", response_model=MealPlanOut)
async def meal_plan_today(
    user: CurrentUser,
    on_date: date | None = Query(default=None, alias="date"),
    service: MealPlanService = Depends(get_meal_plan_service),
) -> MealPlanOut:
    return await service.today(user.id, on_date or date.today())


@router.get("/meal-plans/week", response_model=MealPlanOut)
async def meal_plan_week(
    user: CurrentUser,
    start_date: date | None = Query(default=None),
    service: MealPlanService = Depends(get_meal_plan_service),
) -> MealPlanOut:
    return await service.week(user.id, start_date or date.today())


@router.post("/meal-plans/{meal_plan_id}/regenerate", response_model=MealPlanOut)
async def regenerate_meal_plan(
    meal_plan_id: str,
    payload: MealPlanRegenerateRequest,
    user: CurrentUser,
    service: MealPlanService = Depends(get_meal_plan_service),
) -> MealPlanOut:
    from uuid import UUID

    return await service.regenerate(user.id, UUID(meal_plan_id), payload)


@router.post(
    "/meal-plan-items/{item_id}/replace",
    response_model=MealPlanOut,
)
async def replace_meal_plan_item(
    item_id: str,
    user: CurrentUser,
    service: MealPlanService = Depends(get_meal_plan_service),
    payload: MealPlanReplaceRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> MealPlanOut:
    from uuid import UUID

    reason = payload.replace_reason if payload else "user_requested"
    return await service.replace_item(
        user.id,
        UUID(item_id),
        replace_reason=reason,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/meal-plan-items/{item_id}/complete",
    response_model=MealPlanItemOut,
)
async def complete_meal_plan_item(
    item_id: str,
    user: CurrentUser,
    service: MealPlanService = Depends(get_meal_plan_service),
    completed: bool = True,
) -> MealPlanItemOut:
    from uuid import UUID

    return await service.complete_item(user.id, UUID(item_id), completed=completed)
