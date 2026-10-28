"""ProgressService: weight timeline and daily nutrition balance."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import as_utc
from app.meal_plans.models import MealPlan, MealPlanItem
from app.nutrition.models import NutritionLog
from app.profiles.models import Goal, UserProfile
from app.progress.models import WeightEntry
from app.progress.repository import ProgressRepository
from app.progress.schemas import (
    DailyNutritionBalanceOut,
    ProgressSeriesPointOut,
    ProgressSummaryOut,
    StreakOut,
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
        from app.core.user_time import user_local_date

        profile = (
            await self._session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        today = on_date or user_local_date(profile.timezone if profile else None)
        warnings: list[str] = []
        latest = await self._repository.latest(user_id)
        recent = await self._repository.list_entries(user_id, limit=14)

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

    async def streak(self, user_id: UUID, *, days: int = 180) -> StreakOut:
        from app.core.user_time import local_today_for_user

        today = await local_today_for_user(self._session, user_id)
        start = today - timedelta(days=days - 1)
        log_rows = await self._session.execute(
            select(NutritionLog.logged_on).where(
                NutritionLog.user_id == user_id,
                NutritionLog.logged_on >= start,
            )
        )
        active = set(log_rows.scalars())
        item_rows = await self._session.execute(
            select(MealPlanItem.planned_date)
            .join(MealPlan, MealPlan.id == MealPlanItem.meal_plan_id)
            .where(
                MealPlan.user_id == user_id,
                MealPlanItem.planned_date >= start,
                or_(
                    MealPlanItem.is_completed.is_(True),
                    MealPlanItem.status == "completed",
                ),
            )
        )
        active.update(item_rows.scalars())
        if not active:
            return StreakOut(current_days=0, best_days=0, last_active_date=None)

        cursor = today
        if cursor not in active:
            cursor = today - timedelta(days=1)
        current = 0
        while cursor in active:
            current += 1
            cursor -= timedelta(days=1)

        best = 0
        run = 0
        previous: date | None = None
        for day in sorted(active):
            run = run + 1 if previous == day - timedelta(days=1) else 1
            best = max(best, run)
            previous = day

        return StreakOut(
            current_days=current,
            best_days=best,
            last_active_date=max(active),
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

        day_count = (end_date - start_date).days + 1
        days = [start_date + timedelta(days=offset) for offset in range(day_count)]

        # One batched fetch per source instead of compute_day_consumed per day.
        plan_rows = list(
            (
                await self._session.execute(
                    select(MealPlan).where(
                        MealPlan.user_id == user_id,
                        MealPlan.status == "ready",
                        MealPlan.start_date <= end_date,
                        MealPlan.end_date >= start_date,
                    )
                )
            ).scalars()
        )
        plan_by_day: dict[date, MealPlan] = {}
        for plan in plan_rows:
            cursor = max(plan.start_date, start_date)
            last = min(plan.end_date, end_date)
            while cursor <= last:
                plan_by_day.setdefault(cursor, plan)
                cursor = cursor + timedelta(days=1)

        item_rows = list(
            (
                await self._session.execute(
                    select(MealPlanItem)
                    .join(MealPlan, MealPlan.id == MealPlanItem.meal_plan_id)
                    .where(
                        MealPlan.user_id == user_id,
                        MealPlan.status == "ready",
                        MealPlanItem.planned_date >= start_date,
                        MealPlanItem.planned_date <= end_date,
                    )
                )
            ).scalars()
        )
        items_by_day: dict[date, list[MealPlanItem]] = {}
        for item in item_rows:
            items_by_day.setdefault(item.planned_date, []).append(item)

        log_rows = list(
            (
                await self._session.execute(
                    select(NutritionLog).where(
                        NutritionLog.user_id == user_id,
                        NutritionLog.logged_on >= start_date,
                        NutritionLog.logged_on <= end_date,
                    )
                )
            ).scalars()
        )
        logs_by_day: dict[date, list[NutritionLog]] = {}
        for row in log_rows:
            logs_by_day.setdefault(row.logged_on, []).append(row)

        points: list[ProgressSeriesPointOut] = []
        for day in days:
            items = items_by_day.get(day, [])
            completed = [
                item for item in items
                if item.status == "completed" or item.is_completed
            ]
            consumed = sum(item.calories_kcal for item in completed)
            protein = sum((item.protein_g for item in completed), Decimal("0"))
            fat = sum((item.fat_g for item in completed), Decimal("0"))
            carbs = sum((item.carbohydrate_g for item in completed), Decimal("0"))
            completed_ids = {item.id for item in completed}
            for log in logs_by_day.get(day, []):
                if (
                    log.meal_plan_item_id is not None
                    and log.meal_plan_item_id in completed_ids
                ):
                    continue
                consumed += log.calories_kcal
                protein += log.protein_g
                fat += log.fat_g
                carbs += log.carbohydrate_g
            weight = weight_by_day.get(day)
            if consumed == 0 and not completed and weight is None:
                continue
            points.append(
                ProgressSeriesPointOut(
                    date=day,
                    consumed_kcal=int(consumed),
                    protein_g=protein.quantize(Decimal("0.1")),
                    completed_meals=len(completed),
                    weight_kg=weight,
                )
            )
        return points

    async def _daily_balance(
        self, user_id: UUID, on_date: date, goal: Goal | None
    ) -> DailyNutritionBalanceOut:
        from app.nutrition.day_balance import compute_day_consumed

        balance = await compute_day_consumed(
            self._session, user_id=user_id, on_date=on_date
        )
        target = balance.plan_calorie_target_kcal
        if target is None and goal is not None:
            target = goal.calorie_target_kcal
        return DailyNutritionBalanceOut(
            date=on_date,
            target_calories_kcal=target,
            consumed_calories_kcal=balance.consumed_kcal,
            planned_calories_kcal=balance.planned_kcal,
            protein_g=balance.protein_g.quantize(Decimal("0.1")),
            fat_g=balance.fat_g.quantize(Decimal("0.1")),
            carbohydrate_g=balance.carbs_g.quantize(Decimal("0.1")),
            completed_meals=balance.completed_meals,
            planned_meals=balance.planned_meals,
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
