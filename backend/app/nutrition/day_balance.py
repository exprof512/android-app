"""Shared day consumed totals — single merge of completed plan slots + diary.

Authoritative for Progress and any caller that must match Today ``day_progress``
consumed semantics (planned slots never count unless completed).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meal_plans.models import MealPlan, MealPlanItem
from app.nutrition.models import NutritionLog


@dataclass(frozen=True)
class DayConsumed:
    consumed_kcal: int
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    from_plan_kcal: int
    from_diary_kcal: int
    completed_meals: int
    planned_meals: int
    planned_kcal: int
    plan_calorie_target_kcal: int | None


async def compute_day_consumed(
    session: AsyncSession,
    *,
    user_id: UUID,
    on_date: date,
    plan: MealPlan | None = None,
    items: list[MealPlanItem] | None = None,
) -> DayConsumed:
    """Merge completed meal-plan slots with diary logs (dedupe by item id)."""
    if plan is None:
        from app.meal_plans.selection import find_ready_covering

        plan = await find_ready_covering(session, user_id, on_date)

    if items is None and plan is not None:
        items = list(
            (
                await session.execute(
                    select(MealPlanItem).where(
                        MealPlanItem.meal_plan_id == plan.id,
                        MealPlanItem.planned_date == on_date,
                    )
                )
            ).scalars()
        )
    items = [i for i in (items or []) if i.planned_date == on_date]

    completed = [i for i in items if i.status == "completed" or i.is_completed]
    from_plan_kcal = sum(i.calories_kcal for i in completed)
    consumed_kcal = from_plan_kcal
    protein = sum((i.protein_g for i in completed), Decimal("0"))
    fat = sum((i.fat_g for i in completed), Decimal("0"))
    carbs = sum((i.carbohydrate_g for i in completed), Decimal("0"))
    completed_ids = {i.id for i in completed}

    logs = list(
        (
            await session.execute(
                select(NutritionLog).where(
                    NutritionLog.user_id == user_id,
                    NutritionLog.logged_on == on_date,
                )
            )
        ).scalars()
    )
    from_diary_kcal = 0
    for log in logs:
        if log.meal_plan_item_id is not None and log.meal_plan_item_id in completed_ids:
            continue
        from_diary_kcal += log.calories_kcal
        consumed_kcal += log.calories_kcal
        protein += log.protein_g
        fat += log.fat_g
        carbs += log.carbohydrate_g

    planned_kcal = sum(i.calories_kcal for i in items)
    return DayConsumed(
        consumed_kcal=int(consumed_kcal),
        protein_g=protein,
        fat_g=fat,
        carbs_g=carbs,
        from_plan_kcal=int(from_plan_kcal),
        from_diary_kcal=int(from_diary_kcal),
        completed_meals=len(completed),
        planned_meals=len(items),
        planned_kcal=int(planned_kcal),
        plan_calorie_target_kcal=plan.calorie_target_kcal if plan else None,
    )
