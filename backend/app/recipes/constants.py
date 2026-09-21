"""Recipe domain vocabulary and validation ranges."""

from __future__ import annotations

from decimal import Decimal

RECIPE_UNITS: tuple[str, ...] = ("g", "kg", "ml", "l", "tbsp", "tsp", "piece")
COOKING_METHODS: tuple[str, ...] = (
    "boil",
    "fry",
    "bake",
    "stew",
    "grill",
    "steam",
    "raw",
    "mixed",
)
RECIPE_STATUSES: tuple[str, ...] = ("draft", "ready", "archived")
INGREDIENT_SOURCES: tuple[str, ...] = ("seed", "curated", "import")

MILLILITRES_PER_LITRE = Decimal("1000")
GRAMS_PER_KILOGRAM = Decimal("1000")
TABLESPOON_ML = Decimal("15")
TEASPOON_ML = Decimal("5")

DEFAULT_CATALOG_CURRENCY = "RUB"

NAME_MAX_LENGTH = 255
DESCRIPTION_MAX_LENGTH = 2000
STEP_MAX_LENGTH = 1000
STEPS_MIN = 1
STEPS_MAX = 30
INGREDIENTS_MIN = 1
INGREDIENTS_MAX = 30
COOK_TIME_MINUTES_MIN = 1
COOK_TIME_MINUTES_MAX = 600
SERVINGS_MIN = 1
SERVINGS_MAX = 12
QUANTITY_MIN = Decimal("0.01")
QUANTITY_MAX = Decimal("10000")
GRAMS_MIN = Decimal("0.1")
GRAMS_MAX = Decimal("5000")
TOTAL_GRAMS_MAX = Decimal("30000")

# Deviation above which the recalculated nutrition is reported back as a warning.
CLAIMED_NUTRITION_TOLERANCE = Decimal("0.10")


def sql_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)
