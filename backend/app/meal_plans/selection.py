"""One ready meal plan per user and calendar day.

Every reader (Today, Progress, AI context) must use this ordering.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meal_plans.models import MealPlan


def covering_statement(user_id: UUID, on_date: date):
    return (
        select(MealPlan)
        .where(
            MealPlan.user_id == user_id,
            MealPlan.status == "ready",
            MealPlan.start_date <= on_date,
            MealPlan.end_date >= on_date,
        )
        .order_by(
            MealPlan.updated_at.desc(),
            MealPlan.created_at.desc(),
            MealPlan.id.desc(),
        )
        .limit(1)
    )


async def find_ready_covering(
    session: AsyncSession, user_id: UUID, on_date: date
) -> MealPlan | None:
    return (await session.execute(covering_statement(user_id, on_date))).scalar_one_or_none()
