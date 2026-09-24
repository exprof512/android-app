"""Deterministic meal-plan proposals when OpenAI is unavailable.

Rotates distinct templates per day so fallback weeks are not identical menus.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    MealPlanProposalResponse,
    MealPlanSlotProposal,
    RecipeCandidate,
    RecipeIngredientCandidate,
)
from app.meal_plans import constants
from app.recipes.models import Ingredient

# Multiple options per meal type — indexed by day offset for variety.
# Ingredient names must match seed catalog (0003_recipe_domain).
_BREAKFASTS: list[tuple[str, list[tuple[str, float, str]]]] = [
    ("Овсянка с яблоком", [("Овсяные хлопья", 60, "g"), ("Яблоко", 1, "piece"), ("Творог", 50, "g")]),
    ("Творог с бананом", [("Творог", 150, "g"), ("Банан", 1, "piece")]),
    ("Яичница с овощами", [("Яйцо", 2, "piece"), ("Помидор", 1, "piece"), ("Огурец", 1, "piece")]),
    ("Гречневая каша с молоком", [("Гречка", 60, "g"), ("Молоко", 150, "ml")]),
    ("Йогурт с ягодами", [("Греческий йогурт", 200, "g"), ("Черника", 50, "g")]),
    ("Омлет с сыром", [("Яйцо", 2, "piece"), ("Сыр твёрдый", 30, "g")]),
    ("Смузи-боул", [("Банан", 1, "piece"), ("Греческий йогурт", 150, "g"), ("Овсяные хлопья", 30, "g")]),
]

_LUNCHES: list[tuple[str, list[tuple[str, float, str]]]] = [
    ("Курица с рисом и брокколи", [("Куриная грудка", 150, "g"), ("Рис", 60, "g"), ("Брокколи", 100, "g")]),
    ("Индейка с гречкой", [("Индейка", 150, "g"), ("Гречка", 70, "g"), ("Огурец", 1, "piece")]),
    ("Рыба с картофелем", [("Треска", 150, "g"), ("Картофель", 200, "g"), ("Брокколи", 80, "g")]),
    ("Говядина с чечевицей", [("Говядина", 120, "g"), ("Чечевица", 60, "g"), ("Помидор", 1, "piece")]),
    ("Курица с макаронами", [("Куриная грудка", 140, "g"), ("Макароны", 70, "g"), ("Помидор", 1, "piece")]),
    ("Лосось с рисом", [("Лосось", 120, "g"), ("Рис", 60, "g"), ("Огурец", 1, "piece")]),
    ("Индейка с фасолью", [("Индейка", 140, "g"), ("Фасоль", 60, "g"), ("Брокколи", 100, "g")]),
]

_DINNERS: list[tuple[str, list[tuple[str, float, str]]]] = [
    ("Гречка с яйцом", [("Гречка", 70, "g"), ("Яйцо", 2, "piece"), ("Брокколи", 80, "g")]),
    ("Треска с овощами", [("Треска", 160, "g"), ("Брокколи", 120, "g"), ("Помидор", 1, "piece")]),
    ("Куриная грудка с салатом", [("Куриная грудка", 150, "g"), ("Огурец", 1, "piece"), ("Помидор", 1, "piece")]),
    ("Творожная запеканка", [("Творог", 180, "g"), ("Яйцо", 1, "piece"), ("Банан", 0.5, "piece")]),
    ("Индейка с овощами", [("Индейка", 150, "g"), ("Брокколи", 100, "g"), ("Морковь", 80, "g")]),
    ("Омлет с овощами", [("Яйцо", 3, "piece"), ("Помидор", 1, "piece"), ("Сыр твёрдый", 20, "g")]),
    ("Рыба с гречкой", [("Треска", 150, "g"), ("Гречка", 60, "g"), ("Огурец", 1, "piece")]),
]

_SNACKS: list[tuple[str, list[tuple[str, float, str]]]] = [
    ("Творожный перекус", [("Творог", 150, "g"), ("Яблоко", 1, "piece")]),
    ("Йогурт и банан", [("Греческий йогурт", 150, "g"), ("Банан", 1, "piece")]),
    ("Яблоко с миндалём", [("Яблоко", 1, "piece"), ("Миндаль", 20, "g")]),
    ("Кефир с хлебом", [("Кефир", 200, "ml"), ("Хлеб цельнозерновой", 40, "g")]),
    ("Творог с черникой", [("Творог", 120, "g"), ("Черника", 40, "g")]),
    ("Банан и йогурт", [("Банан", 1, "piece"), ("Греческий йогурт", 100, "g")]),
    ("Овощной перекус", [("Огурец", 1, "piece"), ("Помидор", 1, "piece"), ("Сыр твёрдый", 25, "g")]),
]

_BY_MEAL: dict[str, list[tuple[str, list[tuple[str, float, str]]]]] = {
    "breakfast": _BREAKFASTS,
    "lunch": _LUNCHES,
    "dinner": _DINNERS,
    "snack": _SNACKS,
}


async def build_catalog_meal_plan_proposal(
    session: AsyncSession,
    *,
    start_date: date,
    end_date: date,
    meals_per_day: int,
) -> MealPlanProposalResponse:
    """Build a valid structured proposal from seed catalog ingredients."""
    names: set[str] = set()
    for group in _BY_MEAL.values():
        for _, ingredients in group:
            for item, _, _ in ingredients:
                names.add(item)

    rows = list(
        (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.canonical_name.in_(names),
                    Ingredient.is_active.is_(True),
                )
            )
        ).scalars()
    )
    by_name = {row.canonical_name: row for row in rows}
    missing = [name for name in names if name not in by_name]
    if missing:
        any_rows = list(
            (
                await session.execute(
                    select(Ingredient).where(Ingredient.is_active.is_(True)).limit(24)
                )
            ).scalars()
        )
        if len(any_rows) < 2:
            raise RuntimeError("ingredient_catalog_empty")
        fillers = list(any_rows)
        for i, name in enumerate(missing):
            by_name[name] = fillers[i % len(fillers)]

    meal_cycle = list(
        constants.MEALS_BY_COUNT.get(
            max(1, min(meals_per_day, max(constants.MEALS_BY_COUNT))),
            constants.MEALS_BY_COUNT[3],
        )
    )
    recipes: list[RecipeCandidate] = []
    slots: list[MealPlanSlotProposal] = []
    day = start_date
    recipe_index = 0
    while day <= end_date:
        day_offset = (day - start_date).days
        for meal_type in meal_cycle:
            options = _BY_MEAL.get(meal_type) or _LUNCHES
            name, ingredient_specs = options[day_offset % len(options)]
            ingredients = _ingredients_for(ingredient_specs, by_name)
            recipes.append(
                RecipeCandidate(
                    name=name,
                    description="Каталожный fallback без OpenAI.",
                    servings=1,
                    cooking_method="mixed",
                    cook_time_minutes=25 if meal_type != "snack" else 10,
                    ingredients=ingredients,
                    steps=[
                        "Подготовьте ингредиенты.",
                        "Приготовьте блюдо.",
                        "Подайте к столу.",
                    ],
                    rationale="fallback_catalog",
                )
            )
            slots.append(
                MealPlanSlotProposal(
                    planned_date=day.isoformat(),
                    meal_type=meal_type,  # type: ignore[arg-type]
                    recipe_index=recipe_index,
                    servings=1.0,
                )
            )
            recipe_index += 1
        day += timedelta(days=1)

    return MealPlanProposalResponse(
        recipes=recipes,
        slots=slots,
        rationale="Сгенерировано локально: квота OpenAI недоступна.",
    )


async def build_catalog_food_suggestions(
    session: AsyncSession,
    *,
    count: int = 3,
) -> list[RecipeCandidate]:
    """Deterministic candidates when AI recipes fail domain validation."""
    names = {
        item
        for group in _BY_MEAL.values()
        for _, ingredients in group
        for item, _, _ in ingredients
    }
    rows = list(
        (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.canonical_name.in_(names),
                    Ingredient.is_active.is_(True),
                )
            )
        ).scalars()
    )
    by_name = {row.canonical_name: row for row in rows}
    if len(by_name) < 2:
        any_rows = list(
            (
                await session.execute(
                    select(Ingredient).where(Ingredient.is_active.is_(True)).limit(8)
                )
            ).scalars()
        )
        by_name = {row.canonical_name: row for row in any_rows}
    if len(by_name) < 2:
        return []

    out: list[RecipeCandidate] = []
    flat = [
        (name, meal, specs)
        for meal, group in _BY_MEAL.items()
        for name, specs in group
    ]
    for name, meal_type, ingredient_specs in flat:
        if len(out) >= count:
            break
        ingredients = _ingredients_for(ingredient_specs, by_name)
        out.append(
            RecipeCandidate(
                name=name,
                description="Каталожный fallback: AI-кандидат не прошёл проверку.",
                servings=1,
                cooking_method="mixed",
                cook_time_minutes=25 if meal_type != "snack" else 10,
                ingredients=ingredients,
                steps=[
                    "Подготовьте ингредиенты.",
                    "Приготовьте блюдо.",
                    "Подайте к столу.",
                ],
                rationale="fallback_catalog",
            )
        )
    return out


def catalog_recipe_name_counts(proposal: MealPlanProposalResponse) -> Counter[str]:
    return Counter(r.name for r in proposal.recipes)


def _ingredients_for(
    specs: list[tuple[str, float, str]],
    by_name: dict[str, Ingredient],
) -> list[RecipeIngredientCandidate]:
    available = list(by_name.values())
    out: list[RecipeIngredientCandidate] = []
    for index, (name, qty, unit) in enumerate(specs):
        item = by_name.get(name) or available[index % len(available)]
        out.append(
            RecipeIngredientCandidate(
                name=item.canonical_name,
                quantity=qty,
                unit=unit if unit in {"g", "kg", "ml", "l", "tbsp", "tsp", "piece"} else "g",  # type: ignore[arg-type]
            )
        )
    return out
