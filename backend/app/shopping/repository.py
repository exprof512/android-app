"""Shopping list persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shopping.models import ShoppingList, ShoppingListItem


class ShoppingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, shopping_list: ShoppingList) -> ShoppingList:
        self._session.add(shopping_list)
        await self._session.flush()
        return shopping_list

    async def get(self, list_id: UUID) -> ShoppingList | None:
        statement = (
            select(ShoppingList)
            .where(ShoppingList.id == list_id)
            .options(selectinload(ShoppingList.items))
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_current(
        self, user_id: UUID, *, meal_plan_id: UUID | None = None
    ) -> ShoppingList | None:
        statement = (
            select(ShoppingList)
            .where(ShoppingList.user_id == user_id, ShoppingList.status == "ready")
            .options(selectinload(ShoppingList.items))
            .order_by(ShoppingList.updated_at.desc())
            .limit(1)
        )
        if meal_plan_id is not None:
            statement = statement.where(ShoppingList.meal_plan_id == meal_plan_id)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_item(self, item_id: UUID) -> ShoppingListItem | None:
        return await self._session.get(ShoppingListItem, item_id)

    async def archive_for_plan(self, user_id: UUID, meal_plan_id: UUID) -> None:
        statement = select(ShoppingList).where(
            ShoppingList.user_id == user_id,
            ShoppingList.meal_plan_id == meal_plan_id,
            ShoppingList.status == "ready",
        )
        for row in (await self._session.execute(statement)).scalars():
            row.status = "archived"
