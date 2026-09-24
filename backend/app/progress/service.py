"""ProgressService: weight timeline and daily nutrition balance."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import as_utc
from app.meal_plans.models import MealPlan, MealPlanItem
from app.profiles.models import Goal, UserProfile
from app.progress.models import WeightEntry
from app.progress.repository import ProgressRepository
from app.progress.schemas import (
    DailyNutritionBalanceOut,
    ProgressSeriesPointOut,
    ProgressSummaryOut,
    WeightEntryCreate,
    WeightEntryOut,
)


class ProgressService:
    def __init__(self, *, session: AsyncSession, repository: ProgressRepository) -> None:
        self._session = session
        self._repository = repository

    async def create_weight_entry(
        self, user_id: UUID, payload: WeightEntryCreate
    ) -> WeightEntryOut:
        measured = as_utc(payload.measured_at)
        entry = WeightEntry(
            user_id=user_id,
            weight_kg=Decimal(str(payload.weight_kg)),
            measured_at=measured,
            note=(payload.note or None),
        )
        await self._repository.add(entry)

        profile = (
            await self._session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        if profile is not None:
            profile.current_weight_kg = entry.weight_kg

        await self._session.commit()
        await self._session.refresh(entry)
        return self._entry_out(entry)

    async def list_weight_entries(
        self,
        user_id: UUID,
        *,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> list[WeightEntryOut]:
        rows = await self._repository.list_entries(
            user_id, from_at=from_at, to_at=to_at, limit=180
        )
        return [self._entry_out(row) for row in rows]

    async def summary(
        self,
        user_id: UUID,
        *,
        on_date: date | None = None,
        period: int | None = None,
    ) -> ProgressSummaryOut:
        today = on_date or date.today()
        warnings: list[str] = []
        latest = await self._repository.latest(user_id)
        recent = await self._repository.list_entries(user_id, limit=14)

        profile = (
            await self._session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        goal: Goal | None = None
        if profile is not None and profile.active_goal_id is not None:
            goal = await self._session.get(Goal, profile.active_goal_id)

        current = (
            latest.weight_kg
            if latest is not None
            else (profile.current_weight_kg if profile else None)
        )
        start = goal.start_weight_kg if goal else None
        target = goal.target_weight_kg if goal else None
        goal_type = goal.goal_type if goal else None

        progress_percent: float | None = None
        weight_delta: Decimal | None = None
        if current is not None and start is not None:
            weight_delta = (Decimal(str(current)) - Decimal(str(start))).quantize(
                Decimal("0.01")
            )
        if (
            current is not None
            and start is not None
            and target is not None
            and Decimal(str(start)) != Decimal(str(target))
        ):
            total = Decimal(str(target)) - Decimal(str(start))
            done = Decimal(str(current)) - Decimal(str(start))
            progress_percent = float(
                (done / total * Decimal("100")).quantize(Decimal("0.1"))
            )
            progress_percent = max(0.0, min(100.0, progress_percent))

        trend = self._trend_kg(recent, days=7)
        today_balance = await self._daily_balance(user_id, today, goal)

        if latest is None and current is None:
            warnings.append("Добавьте первую запись веса, чтобы увидеть динамику.")

        series: list[ProgressSeriesPointOut] = []
        period_days = period if period in {7, 30, 90} else None
        if period_days is not None:
            series = await self._build_series(
                user_id, end_date=today, days=period_days, goal=goal
            )

        return ProgressSummaryOut(
            current_weight_kg=current,
            start_weight_kg=start,
            target_weight_kg=target,
            goal_type=goal_type,
            weight_delta_kg=weight_delta,
            progress_percent=progress_percent,
            trend_7d_kg=trend,
            calorie_target_kcal=goal.calorie_target_kcal if goal else None,
            today=today_balance,
            recent_entries=[self._entry_out(row) for row in recent],
            series=series,
            period_days=period_days,
            warnings=warnings,
        )

    async def _build_series(
        self,
        user_id: UUID,
        *,
        end_date: date,
        days: int,
        goal: Goal | None,
    ) -> list[ProgressSeriesPointOut]:
        start_date = end_date - timedelta(days=days - 1)
        entries = await self._repository.list_entries(user_id, limit=500)
        weight_by_day: dict[date, Decimal] = {}
        for entry in entries:
            measured = as_utc(entry.measured_at).date()
            if start_date <= measured <= end_date and measured not in weight_by_day:
                weight_by_day[measured] = Decimal(str(entry.weight_kg))

        points: list[ProgressSeriesPointOut] = []
        cursor = start_date
        while cursor <= end_date:
            balance = await self._daily_balance(user_id, cursor, goal)
            weight = weight_by_day.get(cursor)
            has_activity = (
                balance.consumed_calories_kcal > 0 or balance.completed_meals > 0
            )
            if not has_activity and weight is None:
                cursor = cursor + timedelta(days=1)
                continue
            points.append(
                ProgressSeriesPointOut(
                    date=cursor,
                    consumed_kcal=balance.consumed_calories_kcal,
                    protein_g=balance.protein_g,
                    completed_meals=balance.completed_meals,
                    weight_kg=weight,
                )
            )
            cursor = cursor + timedelta(days=1)
        return points

    async def _daily_balance(
        self, user_id: UUID, on_date: date, goal: Goal | None
    ) -> DailyNutritionBalanceOut:
        plan = (
            await self._session.execute(
                select(MealPlan)
                .where(
                    MealPlan.user_id == user_id,
                    MealPlan.start_date <= on_date,
                    MealPlan.end_date >= on_date,
                    MealPlan.status == "ready",
                )
                .order_by(MealPlan.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if plan is None:
            return DailyNutritionBalanceOut(
                date=on_date,
                target_calories_kcal=goal.calorie_target_kcal if goal else None,
            )

        items = list(
            (
                await self._session.execute(
                    select(MealPlanItem).where(
                        MealPlanItem.meal_plan_id == plan.id,
                        MealPlanItem.planned_date == on_date,
                    )
                )
            ).scalars()
        )
        planned_kcal = sum(item.calories_kcal for item in items)
        completed = [
            item
            for item in items
            if item.status == "completed" or item.is_completed
        ]
        consumed_kcal = sum(item.calories_kcal for item in completed)
        protein = sum((item.protein_g for item in completed), Decimal("0"))
        fat = sum((item.fat_g for item in completed), Decimal("0"))
        carbs = sum((item.carbohydrate_g for item in completed), Decimal("0"))

        # Merge nutrition_logs that are not already tied to a completed meal_plan_item.
        try:
            from app.nutrition.models import NutritionLog

            logs = list(
                (
                    await self._session.execute(
                        select(NutritionLog).where(
                            NutritionLog.user_id == user_id,
                            NutritionLog.logged_on == on_date,
                        )
                    )
                ).scalars()
            )
            completed_item_ids = {item.id for item in completed}
            for log in logs:
                if (
                    log.meal_plan_item_id is not None
                    and log.meal_plan_item_id in completed_item_ids
                ):
                    continue
                consumed_kcal += log.calories_kcal
                protein += log.protein_g
                fat += log.fat_g
                carbs += log.carbohydrate_g
        except Exception:
            pass

        return DailyNutritionBalanceOut(
            date=on_date,
            target_calories_kcal=plan.calorie_target_kcal,
            consumed_calories_kcal=consumed_kcal,
            planned_calories_kcal=planned_kcal,
            protein_g=protein.quantize(Decimal("0.1")),
            fat_g=fat.quantize(Decimal("0.1")),
            carbohydrate_g=carbs.quantize(Decimal("0.1")),
            completed_meals=len(completed),
            planned_meals=len(items),
        )

    @staticmethod
    def _trend_kg(entries: list[WeightEntry], *, days: int) -> Decimal | None:
        if len(entries) < 2:
            return None
        newest = entries[0]
        cutoff = as_utc(newest.measured_at) - timedelta(days=days)
        older = next(
            (row for row in entries if as_utc(row.measured_at) <= cutoff),
            entries[-1],
        )
        if older.id == newest.id:
            return None
        return (Decimal(str(newest.weight_kg)) - Decimal(str(older.weight_kg))).quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _entry_out(entry: WeightEntry) -> WeightEntryOut:
        return WeightEntryOut(
            id=entry.id,
            measured_at=entry.measured_at,
            weight_kg=entry.weight_kg,
            note=entry.note,
        )
