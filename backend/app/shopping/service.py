"""ShoppingService: aggregate recipe ingredients into a checklist."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import OwnershipDenied
from app.core.models import utcnow
from app.meal_plans.errors import MealPlanNotFound
from app.meal_plans.models import MealPlan, MealPlanItem
from app.profiles.models import AvailableProduct
from app.recipes.models import Recipe
from app.recipes.normalization import canonical_key
from app.shopping.errors import ShoppingItemNotFound, ShoppingListNotFound
from app.shopping.models import ShoppingList, ShoppingListItem
from app.shopping.repository import ShoppingRepository
from app.shopping.schemas import (
    ShoppingGenerateRequest,
    ShoppingListItemOut,
    ShoppingListOut,
)


class ShoppingService:
    def __init__(self, *, session: AsyncSession, repository: ShoppingRepository) -> None:
        self._session = session
        self._repository = repository

    async def generate(
        self, user_id: UUID, payload: ShoppingGenerateRequest
    ) -> ShoppingListOut:
        plan = await self._session.get(MealPlan, payload.meal_plan_id)
        if plan is None or plan.user_id != user_id:
            if plan is not None and plan.user_id != user_id:
                raise OwnershipDenied()
            raise MealPlanNotFound()

        from_date = payload.from_date or plan.start_date
        to_date = payload.to_date or plan.end_date
        if to_date < from_date:
            to_date = from_date

        items = list(
            (
                await self._session.execute(
                    select(MealPlanItem)
                    .where(
                        MealPlanItem.meal_plan_id == plan.id,
                        MealPlanItem.planned_date >= from_date,
                        MealPlanItem.planned_date <= to_date,
                    )
                    .options(
                        selectinload(MealPlanItem.recipe).selectinload(Recipe.ingredients)
                    )
                )
            ).scalars()
        )

        aggregated: dict[tuple[str, str], dict] = {}
        for plan_item in items:
            recipe = plan_item.recipe
            if recipe is None:
                continue
            scale = Decimal(str(plan_item.servings)) / Decimal(str(max(recipe.servings, 1)))
            for ingredient in recipe.ingredients:
                normalized = canonical_key(ingredient.display_name)
                key = (normalized, ingredient.unit)
                bucket = aggregated.get(key)
                qty = Decimal(str(ingredient.quantity_value)) * scale
                if bucket is None:
                    aggregated[key] = {
                        "ingredient_id": ingredient.ingredient_id,
                        "normalized_name": normalized,
                        "display_name": ingredient.display_name,
                        "quantity_value": qty,
                        "unit": ingredient.unit,
                        "source_recipe_count": 1,
                    }
                else:
                    bucket["quantity_value"] += qty
                    bucket["source_recipe_count"] += 1

        if payload.exclude_available_products:
            pantry = list(
                (
                    await self._session.execute(
                        select(AvailableProduct).where(AvailableProduct.user_id == user_id)
                    )
                ).scalars()
            )
            pantry_map = {
                (row.normalized_name, row.unit): Decimal(str(row.quantity_value))
                for row in pantry
            }
            for key, bucket in list(aggregated.items()):
                available = pantry_map.get(key)
                if available is None:
                    # also match by normalized name alone with same unit aliases
                    continue
                remaining = bucket["quantity_value"] - available
                if remaining <= 0:
                    del aggregated[key]
                else:
                    bucket["quantity_value"] = remaining

        await self._repository.archive_for_plan(user_id, plan.id)
        shopping_list = ShoppingList(
            user_id=user_id,
            meal_plan_id=plan.id,
            from_date=from_date,
            to_date=to_date,
            status="ready",
            generated_at=utcnow(),
            items=[
                ShoppingListItem(
                    ingredient_id=bucket["ingredient_id"],
                    normalized_name=bucket["normalized_name"],
                    display_name=bucket["display_name"],
                    quantity_value=bucket["quantity_value"].quantize(Decimal("0.01")),
                    unit=bucket["unit"],
                    source_recipe_count=bucket["source_recipe_count"],
                )
                for bucket in sorted(
                    aggregated.values(), key=lambda row: row["display_name"].lower()
                )
            ],
        )
        await self._repository.add(shopping_list)
        await self._session.commit()
        refreshed = await self._repository.get(shopping_list.id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def current(
        self, user_id: UUID, *, meal_plan_id: UUID | None = None
    ) -> ShoppingListOut:
        shopping_list = await self._repository.get_current(
            user_id, meal_plan_id=meal_plan_id
        )
        if shopping_list is None:
            raise ShoppingListNotFound()
        return self._to_out(shopping_list)

    async def get(self, user_id: UUID, list_id: UUID) -> ShoppingListOut:
        shopping_list = await self._repository.get(list_id)
        if shopping_list is None:
            raise ShoppingListNotFound()
        if shopping_list.user_id != user_id:
            raise OwnershipDenied()
        return self._to_out(shopping_list)

    async def complete_item(
        self, user_id: UUID, item_id: UUID, *, completed: bool = True
    ) -> ShoppingListItemOut:
        item = await self._repository.get_item(item_id)
        if item is None:
            raise ShoppingItemNotFound()
        shopping_list = await self._repository.get(item.shopping_list_id)
        if shopping_list is None:
            raise ShoppingListNotFound()
        if shopping_list.user_id != user_id:
            raise OwnershipDenied()
        item.is_completed = completed
        item.completed_at = utcnow() if completed else None
        await self._session.commit()
        await self._session.refresh(item)
        return self._item_out(item)

    def _to_out(self, shopping_list: ShoppingList) -> ShoppingListOut:
        return ShoppingListOut(
            id=shopping_list.id,
            meal_plan_id=shopping_list.meal_plan_id,
            from_date=shopping_list.from_date,
            to_date=shopping_list.to_date,
            status=shopping_list.status,
            items=[self._item_out(item) for item in shopping_list.items],
        )

    @staticmethod
    def _item_out(item: ShoppingListItem) -> ShoppingListItemOut:
        return ShoppingListItemOut(
            id=item.id,
            display_name=item.display_name,
            quantity_value=item.quantity_value,
            unit=item.unit,
            is_completed=item.is_completed,
            source_recipe_count=item.source_recipe_count,
            ingredient_id=item.ingredient_id,
        )
