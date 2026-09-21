"""RecipeEngine: turns a recipe candidate into a canonical recipe or a rejection.

Ingredient names from AI are not canonical until they match the catalog here, and
nutrition always comes from ``NutritionEngine`` over catalog values.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.nutrition.engine import NutrientPortion, NutritionEngine, RecipeNutrition
from app.recipes import constants
from app.recipes.errors import RecipeValidationError
from app.recipes.fingerprint import recipe_fingerprint
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key

_UNSAFE_STEP = re.compile(r"[<>]|https?://|www\.", flags=re.IGNORECASE)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class IngredientDraft:
    name: str
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class RecipeDraft:
    """A candidate recipe; the claimed_* fields are never persisted."""

    name: str
    servings: int
    cooking_method: str
    cook_time_minutes: int
    ingredients: Sequence[IngredientDraft]
    steps: Sequence[str]
    description: str | None = None
    ai_model: str | None = None
    claimed_calories_kcal: int | None = None
    claimed_protein_g: Decimal | None = None
    claimed_fat_g: Decimal | None = None
    claimed_carbohydrate_g: Decimal | None = None


@dataclass(frozen=True)
class CanonicalIngredient:
    ingredient_id: UUID
    display_name: str
    quantity_g: Decimal
    quantity_value: Decimal
    unit: str
    cost_amount: Decimal | None
    sort_order: int


@dataclass(frozen=True)
class CanonicalRecipe:
    """Everything needed to persist a recipe; all numbers are backend output."""

    name: str
    description: str | None
    fingerprint: str
    cooking_method: str
    cook_time_minutes: int
    servings: int
    nutrition: RecipeNutrition
    estimated_cost_amount: Decimal
    currency: str
    steps: list[str]
    ingredients: list[CanonicalIngredient]
    ai_model: str | None = None
    warnings: list[str] = field(default_factory=list)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _grams(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ingredient_grams(ingredient: Ingredient, quantity: Decimal, unit: str) -> Decimal | None:
    """Convert a candidate amount to grams, or None when the catalog cannot."""
    if unit == "g":
        return quantity
    if unit == "kg":
        return quantity * constants.GRAMS_PER_KILOGRAM
    if unit == "piece":
        if ingredient.grams_per_piece is None:
            return None
        return quantity * ingredient.grams_per_piece
    millilitres = {
        "ml": Decimal("1"),
        "l": constants.MILLILITRES_PER_LITRE,
        "tbsp": constants.TABLESPOON_ML,
        "tsp": constants.TEASPOON_ML,
    }.get(unit)
    if millilitres is None or ingredient.density_g_per_ml is None:
        return None
    return quantity * millilitres * ingredient.density_g_per_ml


@dataclass
class _ResolvedIngredient:
    """A catalog match while duplicate mentions are still being merged."""

    catalog_item: Ingredient
    display_name: str
    grams: Decimal
    amounts: list[tuple[Decimal, str]]

    def to_canonical(self, sort_order: int) -> CanonicalIngredient:
        units = {unit for _, unit in self.amounts}
        if len(units) == 1:
            quantity_value = sum((value for value, _ in self.amounts), Decimal("0"))
            unit = self.amounts[0][1]
        else:
            quantity_value, unit = self.grams, "g"
        price = self.catalog_item.reference_price_per_100g
        return CanonicalIngredient(
            ingredient_id=self.catalog_item.id,
            display_name=self.display_name,
            quantity_g=_grams(self.grams),
            quantity_value=_grams(quantity_value),
            unit=unit,
            cost_amount=(
                _money(price * self.grams / Decimal("100")) if price is not None else None
            ),
            sort_order=sort_order,
        )


class RecipeEngine:
    """Validation and canonicalization; it owns no calorie math of its own."""

    def __init__(self, nutrition: NutritionEngine) -> None:
        self._nutrition = nutrition

    def canonicalize(
        self, draft: RecipeDraft, catalog: Mapping[str, Ingredient]
    ) -> CanonicalRecipe:
        details: list[dict[str, str]] = []
        warnings: list[str] = []

        name = _CONTROL_CHARACTERS.sub("", draft.name).strip()
        if not name:
            details.append({"field": "name", "reason": "must_not_be_blank"})
        elif len(name) > constants.NAME_MAX_LENGTH:
            details.append({"field": "name", "reason": "too_long"})

        if draft.cooking_method not in constants.COOKING_METHODS:
            details.append({"field": "cooking_method", "reason": "unsupported_value"})
        if not (
            constants.COOK_TIME_MINUTES_MIN
            <= draft.cook_time_minutes
            <= constants.COOK_TIME_MINUTES_MAX
        ):
            details.append({"field": "cook_time_minutes", "reason": "out_of_range"})
        if not (constants.SERVINGS_MIN <= draft.servings <= constants.SERVINGS_MAX):
            details.append({"field": "servings", "reason": "out_of_range"})

        steps = self._validate_steps(draft.steps, details)
        description = self._validate_description(draft.description, details)
        resolved = self._resolve_ingredients(draft, catalog, details, warnings)

        if details:
            raise RecipeValidationError(details)

        ingredients, currency = resolved
        nutrition = self._nutrition.recipe_nutrition(
            [
                NutrientPortion(
                    grams=item.quantity_g,
                    calories_per_100g=catalog_item.calories_per_100g,
                    protein_per_100g=catalog_item.protein_per_100g,
                    fat_per_100g=catalog_item.fat_per_100g,
                    carbohydrate_per_100g=catalog_item.carbohydrate_per_100g,
                )
                for item, catalog_item in ingredients
            ],
            servings=draft.servings,
        )
        warnings.extend(self._claim_warnings(draft, nutrition))

        canonical_ingredients = [item for item, _ in ingredients]
        total_cost = sum(
            (item.cost_amount or Decimal("0") for item in canonical_ingredients),
            Decimal("0"),
        )
        if all(item.cost_amount is None for item in canonical_ingredients):
            warnings.append(
                "Стоимость неизвестна: у ингредиентов нет справочной цены."
            )

        return CanonicalRecipe(
            name=name,
            description=description,
            fingerprint=recipe_fingerprint(
                name=name,
                cooking_method=draft.cooking_method,
                servings=draft.servings,
                ingredients=[
                    (item.ingredient_id, item.quantity_g)
                    for item in canonical_ingredients
                ],
            ),
            cooking_method=draft.cooking_method,
            cook_time_minutes=draft.cook_time_minutes,
            servings=draft.servings,
            nutrition=nutrition,
            estimated_cost_amount=_money(total_cost / Decimal(draft.servings)),
            currency=currency,
            steps=steps,
            ingredients=canonical_ingredients,
            ai_model=draft.ai_model,
            warnings=warnings,
        )

    def _validate_steps(
        self, steps: Sequence[str], details: list[dict[str, str]]
    ) -> list[str]:
        if not (constants.STEPS_MIN <= len(steps) <= constants.STEPS_MAX):
            details.append({"field": "steps", "reason": "out_of_range"})
        cleaned: list[str] = []
        for index, step in enumerate(steps):
            text = _CONTROL_CHARACTERS.sub("", step).strip()
            if not text:
                details.append({"field": f"steps.{index}", "reason": "must_not_be_blank"})
                continue
            if len(text) > constants.STEP_MAX_LENGTH:
                details.append({"field": f"steps.{index}", "reason": "too_long"})
                continue
            if _UNSAFE_STEP.search(text):
                details.append({"field": f"steps.{index}", "reason": "unsafe_text"})
                continue
            cleaned.append(text)
        return cleaned

    def _validate_description(
        self, description: str | None, details: list[dict[str, str]]
    ) -> str | None:
        if description is None:
            return None
        text = _CONTROL_CHARACTERS.sub("", description).strip()
        if not text:
            return None
        if len(text) > constants.DESCRIPTION_MAX_LENGTH:
            details.append({"field": "description", "reason": "too_long"})
            return None
        if _UNSAFE_STEP.search(text):
            details.append({"field": "description", "reason": "unsafe_text"})
            return None
        return text

    def _resolve_ingredients(
        self,
        draft: RecipeDraft,
        catalog: Mapping[str, Ingredient],
        details: list[dict[str, str]],
        warnings: list[str],
    ) -> tuple[list[tuple[CanonicalIngredient, Ingredient]], str]:
        if not (
            constants.INGREDIENTS_MIN
            <= len(draft.ingredients)
            <= constants.INGREDIENTS_MAX
        ):
            details.append({"field": "ingredients", "reason": "out_of_range"})

        resolved: dict[UUID, _ResolvedIngredient] = {}
        for index, item in enumerate(draft.ingredients):
            field_name = f"ingredients.{index}"
            if not (constants.QUANTITY_MIN <= item.quantity <= constants.QUANTITY_MAX):
                details.append({"field": f"{field_name}.quantity", "reason": "out_of_range"})
                continue
            if item.unit not in constants.RECIPE_UNITS:
                details.append({"field": f"{field_name}.unit", "reason": "unsupported_value"})
                continue

            catalog_item = catalog.get(canonical_key(item.name))
            if catalog_item is None or not catalog_item.is_active:
                details.append({"field": f"{field_name}.name", "reason": "unknown_ingredient"})
                continue

            grams = ingredient_grams(catalog_item, item.quantity, item.unit)
            if grams is None:
                details.append({"field": f"{field_name}.unit", "reason": "unit_not_convertible"})
                continue
            grams = _grams(grams)
            if not (constants.GRAMS_MIN <= grams <= constants.GRAMS_MAX):
                details.append({"field": f"{field_name}.quantity", "reason": "grams_out_of_range"})
                continue

            accumulated = resolved.get(catalog_item.id)
            if accumulated is None:
                resolved[catalog_item.id] = _ResolvedIngredient(
                    catalog_item=catalog_item,
                    display_name=item.name.strip() or catalog_item.canonical_name,
                    grams=grams,
                    amounts=[(item.quantity, item.unit)],
                )
                continue
            accumulated.grams += grams
            accumulated.amounts.append((item.quantity, item.unit))
            warnings.append(
                f"Повторяющийся ингредиент «{accumulated.display_name}» объединён."
            )

        total_grams = sum((item.grams for item in resolved.values()), Decimal("0"))
        if total_grams > constants.TOTAL_GRAMS_MAX:
            details.append({"field": "ingredients", "reason": "total_grams_out_of_range"})

        currencies = {
            item.catalog_item.currency
            for item in resolved.values()
            if item.catalog_item.reference_price_per_100g is not None
            and item.catalog_item.currency
        }
        if len(currencies) > 1:
            details.append({"field": "ingredients", "reason": "mixed_currencies"})
        if details:
            return [], constants.DEFAULT_CATALOG_CURRENCY

        canonical = [
            (item.to_canonical(sort_order), item.catalog_item)
            for sort_order, item in enumerate(resolved.values())
        ]
        currency = currencies.pop() if currencies else constants.DEFAULT_CATALOG_CURRENCY
        return canonical, currency

    @staticmethod
    def _claim_warnings(draft: RecipeDraft, nutrition: RecipeNutrition) -> list[str]:
        """Report, never apply, the values a model claimed for itself."""
        claims = (
            ("калорийности", draft.claimed_calories_kcal, Decimal(nutrition.calories_kcal)),
            ("белка", draft.claimed_protein_g, nutrition.protein_g),
            ("жиров", draft.claimed_fat_g, nutrition.fat_g),
            ("углеводов", draft.claimed_carbohydrate_g, nutrition.carbohydrate_g),
        )
        warnings: list[str] = []
        for label, claimed, calculated in claims:
            if claimed is None:
                continue
            claimed_value = Decimal(claimed)
            if calculated == 0:
                deviates = claimed_value != 0
            else:
                deviates = abs(claimed_value - calculated) / calculated > (
                    constants.CLAIMED_NUTRITION_TOLERANCE
                )
            if deviates:
                warnings.append(
                    f"Значение {label} от модели отклоняется от пересчёта и не сохранено."
                )
        return warnings
