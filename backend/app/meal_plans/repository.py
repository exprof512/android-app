"""Meal plan persistence."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.meal_plans.models import MealPlan, MealPlanItem
from app.recipes.models import Recipe


class MealPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_plan(self, plan_id: UUID) -> MealPlan | None:
        statement = (
            select(MealPlan)
            .where(MealPlan.id == plan_id)
            .options(
                selectinload(MealPlan.items).selectinload(MealPlanItem.recipe)
            )
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_by_hash(self, user_id: UUID, request_hash: str) -> MealPlan | None:
        statement = select(MealPlan).where(
            MealPlan.user_id == user_id,
            MealPlan.generation_request_hash == request_hash,
            MealPlan.status == "ready",
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def find_covering(
        self, user_id: UUID, *, on_date: date
    ) -> MealPlan | None:
        from app.meal_plans.selection import find_ready_covering

        return await find_ready_covering(self._session, user_id, on_date)

    async def get_item(self, item_id: UUID) -> MealPlanItem | None:
        return await self._session.get(MealPlanItem, item_id)

    async def add_plan(self, plan: MealPlan) -> MealPlan:
        self._session.add(plan)
        await self._session.flush()
        return plan

    async def list_items_for_dates(
        self, plan_id: UUID, *, from_date: date, to_date: date
    ) -> list[MealPlanItem]:
        statement = (
            select(MealPlanItem)
            .where(
                MealPlanItem.meal_plan_id == plan_id,
                MealPlanItem.planned_date >= from_date,
                MealPlanItem.planned_date <= to_date,
            )
            .order_by(MealPlanItem.planned_date, MealPlanItem.sort_order)
        )
        return list((await self._session.execute(statement)).scalars())
