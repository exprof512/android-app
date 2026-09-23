"""ShoppingService: aggregate recipe ingredients into a checklist."""

from __future__ import annotations

import hashlib
import re
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
from app.recipes.models import Ingredient, Recipe
from app.recipes.normalization import canonical_key
from app.shopping.errors import ShoppingItemNotFound, ShoppingListNotFound
from app.shopping.models import ShoppingList, ShoppingListItem
from app.shopping.repository import ShoppingRepository
from app.shopping.schemas import (
    ShoppingCategory,
    ShoppingGenerateRequest,
    ShoppingListItemOut,
    ShoppingListOut,
)

_CATEGORY_PATTERNS: list[tuple[ShoppingCategory, re.Pattern[str]]] = [
    (
        "vegetables",
        re.compile(
            r"брокколи|капуст|морков|огур|помидор|томат|лук|перец|салат|шпинат|"
            r"кабачок|баклажан|свёкл|свекл|картофел|чеснок|зелен|яблок|банан|"
            r"ягод|фрукт|овощ|гриб",
            re.IGNORECASE,
        ),
    ),
    (
        "meat",
        re.compile(
            r"курин|говяд|свинин|индейк|рыб|лосос|тунец|фарш|мясо|стейк|"
            r"грудк|филе|бекон|колбас|кревет",
            re.IGNORECASE,
        ),
    ),
    (
        "dairy",
        re.compile(
            r"молок|творог|сыр|йогурт|кефир|сметан|сливк|масло сливоч|"
            r"яйц",
            re.IGNORECASE,
        ),
    ),
    (
        "grains",
        re.compile(
            r"рис|гречк|овёс|овсян|пшен|киноа|макарон|паста|хлеб|мука|"
            r"крупа|булгур|кус-кус|кускус|хлопья",
            re.IGNORECASE,
        ),
    ),
]


def categorize_ingredient(name: str) -> ShoppingCategory:
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(name):
            return category
    return "other"


def plan_items_fingerprint(items: list[MealPlanItem]) -> str:
    recipe_ids = sorted({str(item.recipe_id) for item in items})
    raw = ",".join(recipe_ids)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
        fingerprint = plan_items_fingerprint(items)

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
                cost = (
                    Decimal(str(ingredient.cost_amount)) * scale
                    if ingredient.cost_amount is not None
                    else Decimal("0")
                )
                if bucket is None:
                    aggregated[key] = {
                        "ingredient_id": ingredient.ingredient_id,
                        "normalized_name": normalized,
                        "display_name": ingredient.display_name,
                        "quantity_value": qty,
                        "unit": ingredient.unit,
                        "source_recipe_count": 1,
                        "estimated_cost": cost,
                    }
                else:
                    bucket["quantity_value"] += qty
                    bucket["source_recipe_count"] += 1
                    bucket["estimated_cost"] += cost

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
                    continue
                remaining = bucket["quantity_value"] - available
                if remaining <= 0:
                    del aggregated[key]
                else:
                    # Scale estimated cost proportionally to remaining qty.
                    original = bucket["quantity_value"]
                    if original > 0:
                        bucket["estimated_cost"] = (
                            bucket["estimated_cost"] * remaining / original
                        )
                    bucket["quantity_value"] = remaining

        total = sum(
            (Decimal(str(b["estimated_cost"])) for b in aggregated.values()),
            Decimal("0"),
        ).quantize(Decimal("0.01"))

        await self._repository.archive_for_plan(user_id, plan.id)
        shopping_list = ShoppingList(
            user_id=user_id,
            meal_plan_id=plan.id,
            from_date=from_date,
            to_date=to_date,
            status="ready",
            generated_at=utcnow(),
            stale=False,
            plan_fingerprint=fingerprint,
            estimated_total_amount=total,
            currency="RUB",
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
        # Attach per-item estimated costs via a side map for response.
        self._cost_by_key = {
            (canonical_key(b["display_name"]), b["unit"]): b["estimated_cost"]
            for b in aggregated.values()
        }
        await self._repository.add(shopping_list)
        await self._session.commit()
        refreshed = await self._repository.get(shopping_list.id)
        assert refreshed is not None
        return self._to_out(refreshed, cost_map=self._cost_by_key)

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

    async def clear_completed(
        self, user_id: UUID, *, list_id: UUID | None = None
    ) -> ShoppingListOut:
        if list_id is not None:
            shopping_list = await self._repository.get(list_id)
            if shopping_list is None:
                raise ShoppingListNotFound()
            if shopping_list.user_id != user_id:
                raise OwnershipDenied()
        else:
            shopping_list = await self._repository.get_current(user_id)
            if shopping_list is None:
                raise ShoppingListNotFound()

        remaining = [item for item in shopping_list.items if not item.is_completed]
        for item in list(shopping_list.items):
            if item.is_completed:
                await self._session.delete(item)
        shopping_list.items = remaining
        await self._session.commit()
        refreshed = await self._repository.get(shopping_list.id)
        assert refreshed is not None
        return self._to_out(refreshed)

    def _to_out(
        self,
        shopping_list: ShoppingList,
        *,
        cost_map: dict[tuple[str, str], Decimal] | None = None,
    ) -> ShoppingListOut:
        items_out = [
            self._item_out(
                item,
                estimated_cost=(
                    cost_map.get((item.normalized_name, item.unit))
                    if cost_map is not None
                    else None
                ),
            )
            for item in shopping_list.items
        ]
        estimated_total = shopping_list.estimated_total_amount
        if estimated_total is None and cost_map:
            estimated_total = sum(cost_map.values(), Decimal("0")).quantize(
                Decimal("0.01")
            )
        return ShoppingListOut(
            id=shopping_list.id,
            meal_plan_id=shopping_list.meal_plan_id,
            from_date=shopping_list.from_date,
            to_date=shopping_list.to_date,
            status=shopping_list.status,
            items=items_out,
            estimated_total_amount=estimated_total,
            currency=getattr(shopping_list, "currency", None) or "RUB",
            stale=bool(getattr(shopping_list, "stale", False)),
            plan_fingerprint=getattr(shopping_list, "plan_fingerprint", None),
        )

    @staticmethod
    def _item_out(
        item: ShoppingListItem, *, estimated_cost: Decimal | None = None
    ) -> ShoppingListItemOut:
        return ShoppingListItemOut(
            id=item.id,
            display_name=item.display_name,
            quantity_value=item.quantity_value,
            unit=item.unit,
            is_completed=item.is_completed,
            source_recipe_count=item.source_recipe_count,
            ingredient_id=item.ingredient_id,
            category=categorize_ingredient(item.display_name),
            estimated_cost_amount=estimated_cost,
        )
