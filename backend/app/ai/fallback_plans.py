"""Deterministic meal-plan proposals when OpenAI is unavailable."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

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

_TEMPLATES: list[tuple[str, str, list[tuple[str, float, str]]]] = [
    (
        "Овсянка с яблоком",
        "breakfast",
        [("Овсяные хлопья", 60, "g"), ("Яблоко", 1, "piece"), ("Творог", 50, "g")],
    ),
    (
        "Курица с рисом и брокколи",
        "lunch",
        [("Куриная грудка", 150, "g"), ("Рис", 60, "g"), ("Брокколи", 100, "g")],
    ),
    (
        "Гречка с яйцом",
        "dinner",
        [("Гречка", 70, "g"), ("Яйцо", 2, "piece"), ("Брокколи", 80, "g")],
    ),
    (
        "Творожный перекус",
        "snack",
        [("Творог", 150, "g"), ("Яблоко", 1, "piece")],
    ),
]


async def build_catalog_meal_plan_proposal(
    session: AsyncSession,
    *,
    start_date: date,
    end_date: date,
    meals_per_day: int,
) -> MealPlanProposalResponse:
    """Build a valid structured proposal from seed catalog ingredients."""
    names = {item for _, _, ingredients in _TEMPLATES for item, _, _ in ingredients}
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
        # Fall back to any active ingredients if seed names diverge.
        any_rows = list(
            (
                await session.execute(
                    select(Ingredient).where(Ingredient.is_active.is_(True)).limit(8)
                )
            ).scalars()
        )
        if len(any_rows) < 2:
            raise RuntimeError("ingredient_catalog_empty")
        by_name = {row.canonical_name: row for row in any_rows}

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
        for meal_type in meal_cycle:
            template = next(
                (t for t in _TEMPLATES if t[1] == meal_type),
                _TEMPLATES[recipe_index % len(_TEMPLATES)],
            )
            name, _, ingredient_specs = template
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
    names = {item for _, _, ingredients in _TEMPLATES for item, _, _ in ingredients}
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
    for name, meal_type, ingredient_specs in _TEMPLATES:
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
