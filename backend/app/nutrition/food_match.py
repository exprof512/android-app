"""Match vision / search food names to the ingredient catalog."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.profiles.normalization import normalize_food_name
from app.recipes.aliases import resolve_catalog_key
from app.recipes.models import Ingredient


@dataclass
class MatchedFood:
    ingredient_id: UUID | None
    canonical_name: str
    quantity_g: Decimal | None
    matched: bool
    confidence: float
    calories_kcal: int | None = None
    protein_g: Decimal | None = None
    fat_g: Decimal | None = None
    carbohydrate_g: Decimal | None = None


def nutrition_for_grams(ingredient: Ingredient, grams: Decimal) -> dict[str, Decimal | int]:
    factor = grams / Decimal("100")
    return {
        "calories_kcal": int((ingredient.calories_per_100g * factor).quantize(Decimal("1"))),
        "protein_g": (ingredient.protein_per_100g * factor).quantize(Decimal("0.01")),
        "fat_g": (ingredient.fat_per_100g * factor).quantize(Decimal("0.01")),
        "carbohydrate_g": (ingredient.carbohydrate_per_100g * factor).quantize(
            Decimal("0.01")
        ),
    }


def match_food_name(
    name: str,
    catalog: dict[str, Ingredient],
    *,
    estimated_grams: float | None = None,
    confidence: float = 0.0,
) -> MatchedFood:
    key = resolve_catalog_key(name, catalog)
    grams = Decimal(str(estimated_grams)) if estimated_grams else None
    if key is None:
        return MatchedFood(
            ingredient_id=None,
            canonical_name=name.strip()[:255] or "unknown",
            quantity_g=grams,
            matched=False,
            confidence=confidence,
        )
    ingredient = catalog[key]
    matched = MatchedFood(
        ingredient_id=ingredient.id,
        canonical_name=ingredient.canonical_name,
        quantity_g=grams,
        matched=True,
        confidence=confidence,
    )
    if grams is not None and grams > 0:
        macros = nutrition_for_grams(ingredient, grams)
        matched.calories_kcal = int(macros["calories_kcal"])
        matched.protein_g = macros["protein_g"]  # type: ignore[assignment]
        matched.fat_g = macros["fat_g"]  # type: ignore[assignment]
        matched.carbohydrate_g = macros["carbohydrate_g"]  # type: ignore[assignment]
    return matched


def search_catalog(
    query: str,
    catalog: dict[str, Ingredient],
    *,
    limit: int = 20,
) -> list[Ingredient]:
    needle = normalize_food_name(query)
    if not needle:
        return []
    scored: list[tuple[int, Ingredient]] = []
    for ingredient in catalog.values():
        if not ingredient.is_active:
            continue
        name = normalize_food_name(ingredient.canonical_name)
        if needle == name:
            scored.append((0, ingredient))
        elif name.startswith(needle) or needle in name:
            scored.append((1, ingredient))
    scored.sort(key=lambda pair: (pair[0], pair[1].canonical_name))
    return [item for _, item in scored[:limit]]
