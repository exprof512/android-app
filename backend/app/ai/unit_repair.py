"""Rewrite AI ingredient units that the catalog cannot convert into grams.

AI often returns piece/tbsp/tsp for ingredients whose seed row lacks
grams_per_piece / density_g_per_ml. Nutrition Engine still owns final grams;
this only normalizes amounts so canonicalize can proceed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.ai.schemas import RecipeCandidate, RecipeIngredientCandidate
from app.recipes import constants
from app.recipes.aliases import resolve_catalog_key
from app.recipes.engine import ingredient_grams
from app.recipes.models import Ingredient

# Conservative cooking approximations when catalog conversion is missing.
_DEFAULT_PIECE_GRAMS = Decimal("100")
_TBSP_AS_GRAMS = Decimal("15")
_TSP_AS_GRAMS = Decimal("5")


def repair_recipe_candidate_units(
    candidate: RecipeCandidate,
    catalog: Mapping[str, Ingredient],
) -> tuple[RecipeCandidate, list[str]]:
    """Return candidate with unconvertible units rewritten to grams + warnings."""
    warnings: list[str] = []
    repaired: list[RecipeIngredientCandidate] = []
    changed = False

    for item in candidate.ingredients:
        matched = resolve_catalog_key(item.name, catalog)
        catalog_item = catalog.get(matched) if matched else None
        if catalog_item is None:
            repaired.append(item)
            continue

        quantity = Decimal(str(item.quantity))
        if ingredient_grams(catalog_item, quantity, item.unit) is not None:
            repaired.append(item)
            continue

        approx = _approximate_grams(catalog_item, quantity, item.unit)
        if approx is None:
            repaired.append(item)
            continue

        grams = float(approx.quantize(Decimal("0.01")))
        if grams <= 0:
            repaired.append(item)
            continue

        warnings.append(f"unit_repaired:{item.unit}->g")
        repaired.append(
            item.model_copy(update={"quantity": grams, "unit": "g"})
        )
        changed = True

    if not changed:
        return candidate, warnings
    return candidate.model_copy(update={"ingredients": repaired}), warnings


def _approximate_grams(
    ingredient: Ingredient, quantity: Decimal, unit: str
) -> Decimal | None:
    if unit == "g":
        return quantity
    if unit == "kg":
        return quantity * constants.GRAMS_PER_KILOGRAM
    if unit == "piece":
        if ingredient.grams_per_piece is not None:
            return quantity * ingredient.grams_per_piece
        return quantity * _DEFAULT_PIECE_GRAMS
    if unit == "tbsp":
        if ingredient.density_g_per_ml is not None:
            return quantity * constants.TABLESPOON_ML * ingredient.density_g_per_ml
        return quantity * _TBSP_AS_GRAMS
    if unit == "tsp":
        if ingredient.density_g_per_ml is not None:
            return quantity * constants.TEASPOON_ML * ingredient.density_g_per_ml
        return quantity * _TSP_AS_GRAMS
    if unit == "ml":
        density = ingredient.density_g_per_ml or Decimal("1")
        return quantity * density
    if unit == "l":
        density = ingredient.density_g_per_ml or Decimal("1")
        return quantity * constants.MILLILITRES_PER_LITRE * density
    return None
