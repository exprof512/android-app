"""Shared value ranges for profile schemas and database checks."""

from __future__ import annotations

from decimal import Decimal

AGE_YEARS_MIN = 14
AGE_YEARS_MAX = 120
HEIGHT_CM_MIN = Decimal("100")
HEIGHT_CM_MAX = Decimal("250")
WEIGHT_KG_MIN = Decimal("30")
WEIGHT_KG_MAX = Decimal("400")
MEALS_PER_DAY_MIN = 1
MEALS_PER_DAY_MAX = 8
HOUSEHOLD_SIZE_MIN = 1
HOUSEHOLD_SIZE_MAX = 20
COOK_TIME_MINUTES_MIN = 5
COOK_TIME_MINUTES_MAX = 240
BUDGET_MIN = Decimal("0")
BUDGET_MAX = Decimal("9999999999")
WEEKLY_CHANGE_KG_MIN = Decimal("0")
WEEKLY_CHANGE_KG_MAX = Decimal("2")
CALORIE_VALUE_MIN = 1
CALORIE_VALUE_MAX = 10000
QUANTITY_MIN = Decimal("0")
QUANTITY_MAX = Decimal("99999999")

FOOD_NAME_MAX_LENGTH = 255
FOOD_LIST_MAX_ITEMS = 100
PANTRY_MAX_ITEMS = 200

UNITS: tuple[str, ...] = ("g", "kg", "ml", "l", "piece", "pack", "tbsp", "tsp")
PREFERENCE_TYPES: tuple[str, ...] = ("liked", "disliked")
RESTRICTION_TYPES: tuple[str, ...] = ("allergy", "excluded", "dietary")
GOAL_STATUSES: tuple[str, ...] = ("active", "completed", "abandoned")

DEFAULT_CURRENCY = "RUB"
DEFAULT_TIMEZONE = "Europe/Moscow"


def sql_in_list(values: tuple[str, ...]) -> str:
    """Render a tuple as a SQL IN list for CHECK constraints."""
    return ", ".join(f"'{value}'" for value in values)
