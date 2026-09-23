"""Nutrition diary HTTP API."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.dependencies import get_db_session
from app.nutrition.diary import NutritionDiaryService
from app.nutrition.models import NutritionLog

router = APIRouter(tags=["nutrition"])


class NutritionLogCreate(BaseModel):
    logged_on: date
    meal_type: str
    source: str
    description: str | None = Field(default=None, max_length=255)
    recipe_id: UUID | None = None
    meal_plan_item_id: UUID | None = None
    calories_kcal: int | None = Field(default=None, ge=0, le=10000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=1000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=1000)
    carbohydrate_g: Decimal | None = Field(default=None, ge=0, le=1000)
    servings: Decimal = Field(default=Decimal("1"), gt=0, le=20)


class NutritionLogUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    meal_type: str | None = None
    calories_kcal: int | None = Field(default=None, ge=0, le=10000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=1000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=1000)
    carbohydrate_g: Decimal | None = Field(default=None, ge=0, le=1000)
    servings: Decimal | None = Field(default=None, gt=0, le=20)


class NutritionLogOut(BaseModel):
    id: UUID
    logged_on: date
    meal_type: str
    description: str
    calories_kcal: int
    protein_g: Decimal
    fat_g: Decimal
    carbohydrate_g: Decimal
    servings: Decimal
    source: str
    recipe_id: UUID | None
    meal_plan_item_id: UUID | None

    model_config = {"from_attributes": True}


def _out(row: NutritionLog) -> NutritionLogOut:
    return NutritionLogOut.model_validate(row)


@router.get("/nutrition/logs", response_model=list[NutritionLogOut])
async def list_nutrition_logs(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db_session),
) -> list[NutritionLogOut]:
    rows = await NutritionDiaryService(session).list_logs(user.id, logged_on=date_)
    return [_out(r) for r in rows]


@router.post(
    "/nutrition/logs",
    response_model=NutritionLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_nutrition_log(
    payload: NutritionLogCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> NutritionLogOut:
    row = await NutritionDiaryService(session).create(
        user.id,
        logged_on=payload.logged_on,
        meal_type=payload.meal_type,
        source=payload.source,
        description=payload.description,
        recipe_id=payload.recipe_id,
        meal_plan_item_id=payload.meal_plan_item_id,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        fat_g=payload.fat_g,
        carbohydrate_g=payload.carbohydrate_g,
        servings=payload.servings,
    )
    return _out(row)


@router.patch("/nutrition/logs/{log_id}", response_model=NutritionLogOut)
async def patch_nutrition_log(
    log_id: UUID,
    payload: NutritionLogUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> NutritionLogOut:
    row = await NutritionDiaryService(session).update(
        user.id,
        log_id,
        description=payload.description,
        meal_type=payload.meal_type,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        fat_g=payload.fat_g,
        carbohydrate_g=payload.carbohydrate_g,
        servings=payload.servings,
    )
    return _out(row)


@router.delete("/nutrition/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nutrition_log(
    log_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await NutritionDiaryService(session).delete(user.id, log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
