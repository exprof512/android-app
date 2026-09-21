"""MealPlanEngine: constraint checks that AI proposals must pass."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.meal_plans import constants
from app.meal_plans.errors import PlanConstraintsUnsatisfied
from app.profiles.normalization import normalize_food_name
from app.recipes.models import Recipe


@dataclass(frozen=True)
class PlannedSlot:
    planned_date: date
    meal_type: str
    sort_order: int
    servings: Decimal
    recipe: Recipe


@dataclass(frozen=True)
class DayTargets:
    calories_kcal: int
    protein_g: Decimal
    fat_g: Decimal
    carbohydrate_g: Decimal


class MealPlanEngine:
    """Validates assembled day/week plans; does not call AI."""

    def validate_plan(
        self,
        *,
        slots: Sequence[PlannedSlot],
        targets: DayTargets,
        meals_per_day: int,
        max_cook_time_minutes: int | None,
        restricted_names: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> list[str]:
        details: list[dict[str, str]] = []
        warnings: list[str] = []
        restricted = {normalize_food_name(name) for name in restricted_names}
        restricted.discard("")

        by_day: dict[date, list[PlannedSlot]] = defaultdict(list)
        for slot in slots:
            if slot.planned_date < start_date or slot.planned_date > end_date:
                details.append(
                    {
                        "field": "planned_date",
                        "reason": "outside_plan_range",
                    }
                )
            if slot.meal_type not in constants.MEAL_TYPES:
                details.append({"field": "meal_type", "reason": "invalid"})
            by_day[slot.planned_date].append(slot)

            if (
                max_cook_time_minutes is not None
                and slot.recipe.cook_time_minutes > max_cook_time_minutes
            ):
                details.append(
                    {
                        "field": "cook_time_minutes",
                        "reason": "exceeds_user_limit",
                    }
                )

            for ingredient in slot.recipe.ingredients:
                key = normalize_food_name(ingredient.display_name)
                if key and key in restricted:
                    details.append(
                        {
                            "field": "ingredients",
                            "reason": f"restricted:{key}",
                        }
                    )

        expected_meals = constants.MEALS_BY_COUNT.get(
            meals_per_day, constants.MEALS_BY_COUNT[4]
        )
        cursor = start_date
        while cursor <= end_date:
            day_slots = by_day.get(cursor, [])
            if len(day_slots) != len(expected_meals):
                details.append(
                    {
                        "field": "meals_per_day",
                        "reason": f"expected_{len(expected_meals)}_got_{len(day_slots)}",
                    }
                )
            day_calories = sum(
                int(round(slot.recipe.calories_kcal * float(slot.servings)))
                for slot in day_slots
            )
            low = int(targets.calories_kcal * (1 - constants.DAILY_CALORIE_TOLERANCE))
            high = int(targets.calories_kcal * (1 + constants.DAILY_CALORIE_TOLERANCE))
            if day_slots and not (low <= day_calories <= high):
                details.append(
                    {
                        "field": "daily_calories",
                        "reason": f"out_of_range:{day_calories}",
                    }
                )
                warnings.append(
                    f"Калории за {cursor.isoformat()} ({day_calories}) вне допуска "
                    f"{low}–{high}."
                )
            cursor = date.fromordinal(cursor.toordinal() + 1)

        if details:
            # Deduplicate while preserving order.
            unique: list[dict[str, str]] = []
            seen: set[tuple[str, str]] = set()
            for item in details:
                key = (item["field"], item["reason"])
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            raise PlanConstraintsUnsatisfied(unique)
        return warnings
