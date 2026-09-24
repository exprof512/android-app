"""Nutrition diary HTTP API — food journal + photo analysis."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.user_time import local_today_for_user
from app.core.dependencies import get_db_session, get_services
from app.core.errors import ApiError
from app.core.services import Services
from app.entitlements.repository import EntitlementsRepository
from app.entitlements.service import EntitlementsService
from app.nutrition.diary import NutritionDiaryService
from app.nutrition.food_match import nutrition_for_grams, search_catalog
from app.nutrition.models import MealTemplate, MealTemplateItem, NutritionLog
from app.nutrition.photo import (
    PhotoAnalysisService,
    PhotoConfirmIn,
    build_vision_provider,
)
from app.recipes.models import Ingredient
from app.recipes.repository import RecipeRepository

router = APIRouter(tags=["nutrition"])


async def _user_today(session: AsyncSession, user_id: UUID) -> date:
    return await local_today_for_user(session, user_id)


class NutritionLogCreate(BaseModel):
    logged_on: date
    meal_type: str
    source: str
    description: str | None = Field(default=None, max_length=255)
    recipe_id: UUID | None = None
    meal_plan_item_id: UUID | None = None
    ingredient_id: UUID | None = None
    calories_kcal: int | None = Field(default=None, ge=0, le=10000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=1000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=1000)
    carbohydrate_g: Decimal | None = Field(default=None, ge=0, le=1000)
    servings: Decimal = Field(default=Decimal("1"), gt=0, le=20)
    quantity_g: Decimal | None = Field(default=None, gt=0, le=5000)
    unit: str | None = Field(default=None, max_length=16)
    notes: str | None = Field(default=None, max_length=500)


class NutritionLogUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    meal_type: str | None = None
    calories_kcal: int | None = Field(default=None, ge=0, le=10000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=1000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=1000)
    carbohydrate_g: Decimal | None = Field(default=None, ge=0, le=1000)
    servings: Decimal | None = Field(default=None, gt=0, le=20)
    quantity_g: Decimal | None = Field(default=None, gt=0, le=5000)
    ingredient_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=500)


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
    ingredient_id: UUID | None = None
    quantity_g: Decimal | None = None
    unit: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class FoodSearchHit(BaseModel):
    ingredient_id: UUID
    name: str
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbohydrate_per_100g: float


class FoodCalculateIn(BaseModel):
    ingredient_id: UUID
    quantity_g: float = Field(gt=0, le=5000)


class FoodCalculateOut(BaseModel):
    ingredient_id: UUID
    name: str
    quantity_g: float
    calories_kcal: int
    protein_g: float
    fat_g: float
    carbohydrate_g: float


class MealTemplateItemIn(BaseModel):
    ingredient_id: UUID | None = None
    recipe_id: UUID | None = None
    description: str = Field(min_length=1, max_length=255)
    quantity_g: float | None = Field(default=None, gt=0, le=5000)
    servings: float = Field(default=1, gt=0, le=20)


class MealTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    meal_type: str = "breakfast"
    items: list[MealTemplateItemIn] = Field(min_length=1, max_length=20)


class MealTemplateOut(BaseModel):
    id: UUID
    name: str
    meal_type: str
    items: list[dict]

    model_config = {"from_attributes": True}


def _out(row: NutritionLog) -> NutritionLogOut:
    return NutritionLogOut.model_validate(row)


def _photo_service(
    request: Request,
    session: AsyncSession,
    services: Services,
) -> PhotoAnalysisService:
    settings = request.app.state.settings
    vision = getattr(request.app.state, "vision_provider", None)
    if vision is None:
        vision = build_vision_provider(settings)
        if settings.app_env != "test":
            request.app.state.vision_provider = vision
    entitlements = EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=settings,
    )
    return PhotoAnalysisService(
        session=session,
        vision=vision,
        entitlements=entitlements,
        settings=settings,
        vision_model=settings.openai_vision_model or "gpt-4.1-mini",
    )


@router.get("/nutrition/logs", response_model=list[NutritionLogOut])
async def list_nutrition_logs(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db_session),
) -> list[NutritionLogOut]:
    rows = await NutritionDiaryService(session).list_logs(user.id, logged_on=date_)
    return [_out(r) for r in rows]


@router.get("/nutrition/diary/day")
async def diary_day(
    user: CurrentUser,
    date_: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await NutritionDiaryService(session).day_summary(
        user.id, date_ or await _user_today(session, user.id)
    )


@router.get("/nutrition/diary/history")
async def diary_history(
    user: CurrentUser,
    days: int = Query(default=7, ge=1, le=31),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await NutritionDiaryService(session).history(
        user.id, days=days, end=await _user_today(session, user.id)
    )


@router.get("/nutrition/foods/recent")
async def recent_foods(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await NutritionDiaryService(session).recent_foods(user.id)


@router.get("/nutrition/foods/search", response_model=list[FoodSearchHit])
async def search_foods(
    user: CurrentUser,
    q: str = Query(min_length=1, max_length=80),
    session: AsyncSession = Depends(get_db_session),
) -> list[FoodSearchHit]:
    del user
    catalog = await RecipeRepository(session).active_catalog()
    hits = search_catalog(q, catalog, limit=20)
    return [
        FoodSearchHit(
            ingredient_id=item.id,
            name=item.canonical_name,
            calories_per_100g=float(item.calories_per_100g),
            protein_per_100g=float(item.protein_per_100g),
            fat_per_100g=float(item.fat_per_100g),
            carbohydrate_per_100g=float(item.carbohydrate_per_100g),
        )
        for item in hits
    ]


@router.post("/nutrition/foods/calculate", response_model=FoodCalculateOut)
async def calculate_food(
    payload: FoodCalculateIn,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> FoodCalculateOut:
    del user
    ingredient = await session.get(Ingredient, payload.ingredient_id)
    if ingredient is None or not ingredient.is_active:
        raise ApiError(
            status_code=404, code="ingredient_not_found", message="Продукт не найден."
        )
    macros = nutrition_for_grams(ingredient, Decimal(str(payload.quantity_g)))
    return FoodCalculateOut(
        ingredient_id=ingredient.id,
        name=ingredient.canonical_name,
        quantity_g=payload.quantity_g,
        calories_kcal=int(macros["calories_kcal"]),
        protein_g=float(macros["protein_g"]),  # type: ignore[arg-type]
        fat_g=float(macros["fat_g"]),  # type: ignore[arg-type]
        carbohydrate_g=float(macros["carbohydrate_g"]),  # type: ignore[arg-type]
    )


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
        ingredient_id=payload.ingredient_id,
        calories_kcal=payload.calories_kcal,
        protein_g=payload.protein_g,
        fat_g=payload.fat_g,
        carbohydrate_g=payload.carbohydrate_g,
        servings=payload.servings,
        quantity_g=payload.quantity_g,
        unit=payload.unit,
        notes=payload.notes,
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
        quantity_g=payload.quantity_g,
        ingredient_id=payload.ingredient_id,
        notes=payload.notes,
    )
    return _out(row)


@router.post(
    "/nutrition/logs/{log_id}/duplicate",
    response_model=NutritionLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_nutrition_log(
    log_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> NutritionLogOut:
    row = await NutritionDiaryService(session).duplicate(user.id, log_id)
    return _out(row)


@router.delete("/nutrition/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nutrition_log(
    log_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await NutritionDiaryService(session).delete(user.id, log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/nutrition/photo/analyze")
async def analyze_food_photo(
    request: Request,
    user: CurrentUser,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
):
    data = await file.read()
    service = _photo_service(request, session, services)
    result = await service.analyze(
        user.id,
        image_bytes=data,
        mime_type=file.content_type or "image/jpeg",
    )
    await session.commit()
    return result


@router.post("/nutrition/photo/recalculate", response_model=FoodCalculateOut)
async def recalculate_photo_item(
    payload: FoodCalculateIn,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> FoodCalculateOut:
    del user
    # Same authoritative calc as search path.
    ingredient = await session.get(Ingredient, payload.ingredient_id)
    if ingredient is None:
        raise ApiError(
            status_code=404, code="ingredient_not_found", message="Продукт не найден."
        )
    macros = nutrition_for_grams(ingredient, Decimal(str(payload.quantity_g)))
    return FoodCalculateOut(
        ingredient_id=ingredient.id,
        name=ingredient.canonical_name,
        quantity_g=payload.quantity_g,
        calories_kcal=int(macros["calories_kcal"]),
        protein_g=float(macros["protein_g"]),  # type: ignore[arg-type]
        fat_g=float(macros["fat_g"]),  # type: ignore[arg-type]
        carbohydrate_g=float(macros["carbohydrate_g"]),  # type: ignore[arg-type]
    )


@router.post(
    "/nutrition/photo/confirm",
    response_model=list[NutritionLogOut],
    status_code=status.HTTP_201_CREATED,
)
async def confirm_food_photo(
    payload: PhotoConfirmIn,
    request: Request,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> list[NutritionLogOut]:
    service = _photo_service(request, session, services)
    rows = await service.confirm(
        user.id,
        logged_on=payload.logged_on,
        meal_type=payload.meal_type,
        items=payload.items,
        idempotency_key=idempotency_key,
    )
    await session.commit()
    return [_out(r) for r in rows]


@router.get("/nutrition/meal-templates", response_model=list[MealTemplateOut])
async def list_meal_templates(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[MealTemplateOut]:
    templates = list(
        (
            await session.execute(
                select(MealTemplate).where(MealTemplate.user_id == user.id)
            )
        ).scalars()
    )
    out: list[MealTemplateOut] = []
    for tmpl in templates:
        items = list(
            (
                await session.execute(
                    select(MealTemplateItem)
                    .where(MealTemplateItem.template_id == tmpl.id)
                    .order_by(MealTemplateItem.sort_order)
                )
            ).scalars()
        )
        out.append(
            MealTemplateOut(
                id=tmpl.id,
                name=tmpl.name,
                meal_type=tmpl.meal_type,
                items=[
                    {
                        "id": str(i.id),
                        "description": i.description,
                        "ingredient_id": str(i.ingredient_id) if i.ingredient_id else None,
                        "recipe_id": str(i.recipe_id) if i.recipe_id else None,
                        "quantity_g": float(i.quantity_g) if i.quantity_g else None,
                        "servings": float(i.servings),
                    }
                    for i in items
                ],
            )
        )
    return out


@router.post(
    "/nutrition/meal-templates",
    response_model=MealTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_meal_template(
    payload: MealTemplateCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> MealTemplateOut:
    tmpl = MealTemplate(
        user_id=user.id, name=payload.name[:120], meal_type=payload.meal_type
    )
    session.add(tmpl)
    await session.flush()
    for index, item in enumerate(payload.items):
        session.add(
            MealTemplateItem(
                template_id=tmpl.id,
                ingredient_id=item.ingredient_id,
                recipe_id=item.recipe_id,
                description=item.description[:255],
                quantity_g=(
                    Decimal(str(item.quantity_g)) if item.quantity_g is not None else None
                ),
                servings=Decimal(str(item.servings)),
                sort_order=index,
            )
        )
    await session.commit()
    return MealTemplateOut(
        id=tmpl.id,
        name=tmpl.name,
        meal_type=tmpl.meal_type,
        items=[
            {
                "description": i.description,
                "ingredient_id": str(i.ingredient_id) if i.ingredient_id else None,
                "quantity_g": i.quantity_g,
                "servings": i.servings,
            }
            for i in payload.items
        ],
    )


@router.post(
    "/nutrition/meal-templates/{template_id}/apply",
    response_model=list[NutritionLogOut],
    status_code=status.HTTP_201_CREATED,
)
async def apply_meal_template(
    template_id: UUID,
    user: CurrentUser,
    logged_on: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[NutritionLogOut]:
    tmpl = await session.get(MealTemplate, template_id)
    if tmpl is None or tmpl.user_id != user.id:
        raise ApiError(
            status_code=404, code="meal_template_not_found", message="Шаблон не найден."
        )
    items = list(
        (
            await session.execute(
                select(MealTemplateItem).where(MealTemplateItem.template_id == tmpl.id)
            )
        ).scalars()
    )
    day = logged_on or await _user_today(session, user.id)
    diary = NutritionDiaryService(session)
    created: list[NutritionLog] = []
    for item in items:
        if item.ingredient_id and item.quantity_g:
            row = await diary.create(
                user.id,
                logged_on=day,
                meal_type=tmpl.meal_type,
                source="search",
                description=item.description,
                ingredient_id=item.ingredient_id,
                quantity_g=item.quantity_g,
                unit="g",
            )
        elif item.recipe_id:
            row = await diary.create(
                user.id,
                logged_on=day,
                meal_type=tmpl.meal_type,
                source="recipe",
                recipe_id=item.recipe_id,
                servings=item.servings,
                description=item.description,
            )
        else:
            continue
        created.append(row)
    return [_out(r) for r in created]
