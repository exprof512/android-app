"""Meal plan vocabulary."""

from __future__ import annotations

MEAL_TYPES: tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")
MEAL_PLAN_STATUSES: tuple[str, ...] = ("draft", "ready", "archived")
MEAL_ITEM_STATUSES: tuple[str, ...] = ("planned", "replaced", "completed", "skipped")

# Default slot order for N meals/day.
MEALS_BY_COUNT: dict[int, tuple[str, ...]] = {
    1: ("lunch",),
    2: ("breakfast", "dinner"),
    3: ("breakfast", "lunch", "dinner"),
    4: ("breakfast", "lunch", "dinner", "snack"),
    5: ("breakfast", "lunch", "dinner", "snack", "snack"),
    6: ("breakfast", "snack", "lunch", "snack", "dinner", "snack"),
    7: ("breakfast", "snack", "lunch", "snack", "dinner", "snack", "snack"),
    8: (
        "breakfast",
        "snack",
        "lunch",
        "snack",
        "dinner",
        "snack",
        "snack",
        "snack",
    ),
}

# Daily totals may deviate within this relative band before rejection.
DAILY_CALORIE_TOLERANCE = 0.20
DAYS_MIN = 1
DAYS_MAX = 7


def sql_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)
