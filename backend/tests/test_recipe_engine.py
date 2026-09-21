from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.nutrition.engine import DEFAULT_ACTIVITY_FACTORS, NutritionEngine
from app.recipes.engine import (
    IngredientDraft,
    RecipeDraft,
    RecipeEngine,
    ingredient_grams,
)
from app.recipes.errors import RecipeValidationError
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key


def catalog_ingredient(
    canonical_name: str,
    *,
    calories: str,
    protein: str,
    fat: str,
    carbohydrate: str,
    unit: str = "g",
    price: str | None = None,
    currency: str | None = "RUB",
    grams_per_piece: str | None = None,
    density: str | None = None,
    is_active: bool = True,
) -> Ingredient:
    return Ingredient(
        id=uuid4(),
        canonical_name=canonical_name,
        normalized_name=canonical_key(canonical_name),
        default_unit=unit,
        calories_per_100g=Decimal(calories),
        protein_per_100g=Decimal(protein),
        fat_per_100g=Decimal(fat),
        carbohydrate_per_100g=Decimal(carbohydrate),
        reference_price_per_100g=None if price is None else Decimal(price),
        currency=None if price is None else currency,
        grams_per_piece=None if grams_per_piece is None else Decimal(grams_per_piece),
        density_g_per_ml=None if density is None else Decimal(density),
        source="seed",
        is_active=is_active,
    )


CHICKEN = catalog_ingredient(
    "Куриная грудка", calories="165", protein="31", fat="3.6", carbohydrate="0", price="45"
)
RICE = catalog_ingredient(
    "Рис", calories="344", protein="7", fat="1", carbohydrate="78", price="10"
)
OLIVE_OIL = catalog_ingredient(
    "Оливковое масло",
    calories="884",
    protein="0",
    fat="100",
    carbohydrate="0",
    unit="ml",
    price="90",
    density="0.92",
)
EGG = catalog_ingredient(
    "Яйцо",
    calories="157",
    protein="13",
    fat="11",
    carbohydrate="1.1",
    unit="piece",
    price="12",
    grams_per_piece="55",
)
WATER = catalog_ingredient(
    "Вода", calories="0", protein="0", fat="0", carbohydrate="0", unit="ml", density="1.0"
)
SALT = catalog_ingredient("Соль", calories="0", protein="0", fat="0", carbohydrate="0")


def build_catalog(*ingredients: Ingredient) -> dict[str, Ingredient]:
    return {ingredient.normalized_name: ingredient for ingredient in ingredients}


def build_engine() -> RecipeEngine:
    return RecipeEngine(
        NutritionEngine(
            activity_factors=dict(DEFAULT_ACTIVITY_FACTORS),
            min_daily_calories_female=1200,
            min_daily_calories_male=1500,
            max_weekly_weight_change_kg=Decimal("1.0"),
        )
    )


def build_draft(**overrides) -> RecipeDraft:
    values = {
        "name": "Курица с рисом",
        "servings": 2,
        "cooking_method": "fry",
        "cook_time_minutes": 30,
        "ingredients": [
            IngredientDraft(name="куриная грудка", quantity=Decimal("200"), unit="g"),
            IngredientDraft(name="рис", quantity=Decimal("100"), unit="g"),
            IngredientDraft(name="оливковое масло", quantity=Decimal("1"), unit="tbsp"),
        ],
        "steps": ["Обжарить курицу.", "Отварить рис.", "Смешать и подать."],
    }
    values.update(overrides)
    return RecipeDraft(**values)


def reasons(error: RecipeValidationError) -> list[tuple[str, str]]:
    return [(detail["field"], detail["reason"]) for detail in error.details or []]


@pytest.mark.parametrize(
    ("ingredient", "quantity", "unit", "expected"),
    [
        (CHICKEN, "200", "g", "200"),
        (CHICKEN, "1.5", "kg", "1500"),
        (WATER, "250", "ml", "250.0"),
        (WATER, "1", "l", "1000.0"),
        (OLIVE_OIL, "1", "tbsp", "13.80"),
        (OLIVE_OIL, "1", "tsp", "4.60"),
        (EGG, "3", "piece", "165"),
    ],
)
def test_units_convert_to_grams(
    ingredient: Ingredient, quantity: str, unit: str, expected: str
) -> None:
    grams = ingredient_grams(ingredient, Decimal(quantity), unit)

    assert grams == Decimal(expected)


def test_units_without_catalog_data_are_not_convertible() -> None:
    assert ingredient_grams(CHICKEN, Decimal("1"), "piece") is None
    assert ingredient_grams(CHICKEN, Decimal("100"), "ml") is None
    assert ingredient_grams(SALT, Decimal("1"), "tsp") is None


def test_nutrition_and_cost_come_from_the_catalog() -> None:
    recipe = build_engine().canonicalize(
        build_draft(), build_catalog(CHICKEN, RICE, OLIVE_OIL)
    )

    assert recipe.nutrition.calories_kcal == 398
    assert recipe.nutrition.protein_g == Decimal("34.50")
    assert recipe.nutrition.fat_g == Decimal("11.00")
    assert recipe.nutrition.carbohydrate_g == Decimal("39.00")
    assert recipe.estimated_cost_amount == Decimal("56.21")
    assert recipe.currency == "RUB"
    assert [item.quantity_g for item in recipe.ingredients] == [
        Decimal("200.00"),
        Decimal("100.00"),
        Decimal("13.80"),
    ]
    assert [item.cost_amount for item in recipe.ingredients] == [
        Decimal("90.00"),
        Decimal("10.00"),
        Decimal("12.42"),
    ]
    assert recipe.warnings == []


def test_display_quantity_and_unit_survive_canonicalization() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            ingredients=[
                IngredientDraft(name="Оливковое масло", quantity=Decimal("2"), unit="tbsp")
            ]
        ),
        build_catalog(OLIVE_OIL),
    )

    item = recipe.ingredients[0]
    assert item.display_name == "Оливковое масло"
    assert (item.quantity_value, item.unit) == (Decimal("2.00"), "tbsp")
    assert item.quantity_g == Decimal("27.60")


def test_ai_claimed_nutrition_is_reported_but_never_applied() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            claimed_calories_kcal=250,
            claimed_protein_g=Decimal("60"),
            claimed_fat_g=Decimal("11"),
        ),
        build_catalog(CHICKEN, RICE, OLIVE_OIL),
    )

    assert recipe.nutrition.calories_kcal == 398
    assert recipe.nutrition.protein_g == Decimal("34.50")
    assert any("калорийности" in warning for warning in recipe.warnings)
    assert any("белка" in warning for warning in recipe.warnings)
    # Fat was claimed within tolerance, so it produces no warning.
    assert not any("жиров" in warning for warning in recipe.warnings)


def test_claims_within_tolerance_stay_silent() -> None:
    recipe = build_engine().canonicalize(
        build_draft(claimed_calories_kcal=400),
        build_catalog(CHICKEN, RICE, OLIVE_OIL),
    )

    assert recipe.warnings == []


def test_unknown_and_inactive_ingredients_are_rejected() -> None:
    retired = catalog_ingredient(
        "Маргарин",
        calories="717",
        protein="0",
        fat="80",
        carbohydrate="1",
        is_active=False,
    )

    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(
                ingredients=[
                    IngredientDraft(name="драконий перец", quantity=Decimal("10"), unit="g"),
                    IngredientDraft(name="маргарин", quantity=Decimal("10"), unit="g"),
                ]
            ),
            build_catalog(retired),
        )

    assert error.value.status_code == 422
    assert error.value.code == "recipe_validation_error"
    assert reasons(error.value) == [
        ("ingredients.0.name", "unknown_ingredient"),
        ("ingredients.1.name", "unknown_ingredient"),
    ]


def test_non_convertible_unit_is_rejected() -> None:
    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(
                ingredients=[
                    IngredientDraft(name="куриная грудка", quantity=Decimal("2"), unit="piece")
                ]
            ),
            build_catalog(CHICKEN),
        )

    assert reasons(error.value) == [("ingredients.0.unit", "unit_not_convertible")]


def test_ingredient_names_are_matched_case_and_punctuation_insensitively() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            ingredients=[
                IngredientDraft(name="  КУРИНАЯ   Грудка. ", quantity=Decimal("150"), unit="g")
            ]
        ),
        build_catalog(CHICKEN),
    )

    item = recipe.ingredients[0]
    assert item.ingredient_id == CHICKEN.id
    # The dish card shows the catalog spelling, not what the candidate wrote.
    assert item.display_name == "Куриная грудка"


def test_repeated_ingredient_is_merged() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            servings=1,
            ingredients=[
                IngredientDraft(name="рис", quantity=Decimal("60"), unit="g"),
                IngredientDraft(name="Рис", quantity=Decimal("40"), unit="g"),
            ],
        ),
        build_catalog(RICE),
    )

    assert len(recipe.ingredients) == 1
    item = recipe.ingredients[0]
    assert item.quantity_g == Decimal("100.00")
    assert (item.quantity_value, item.unit) == (Decimal("100.00"), "g")
    assert any("объединён" in warning for warning in recipe.warnings)


def test_merged_ingredient_with_mixed_units_is_displayed_in_grams() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            servings=1,
            ingredients=[
                IngredientDraft(name="оливковое масло", quantity=Decimal("1"), unit="tbsp"),
                IngredientDraft(name="оливковое масло", quantity=Decimal("10"), unit="ml"),
            ],
        ),
        build_catalog(OLIVE_OIL),
    )

    item = recipe.ingredients[0]
    assert item.quantity_g == Decimal("23.00")
    assert (item.quantity_value, item.unit) == (Decimal("23.00"), "g")


def test_ingredients_without_a_price_produce_a_cost_warning() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            servings=1,
            ingredients=[IngredientDraft(name="вода", quantity=Decimal("500"), unit="ml")],
            steps=["Налить воду."],
        ),
        build_catalog(WATER),
    )

    assert recipe.estimated_cost_amount == Decimal("0.00")
    assert recipe.currency == "RUB"
    assert any("Стоимость неизвестна" in warning for warning in recipe.warnings)


def test_mixed_price_currencies_are_rejected() -> None:
    euro_rice = catalog_ingredient(
        "Рис", calories="344", protein="7", fat="1", carbohydrate="78", price="2", currency="EUR"
    )

    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(
                ingredients=[
                    IngredientDraft(name="куриная грудка", quantity=Decimal("100"), unit="g"),
                    IngredientDraft(name="рис", quantity=Decimal("100"), unit="g"),
                ]
            ),
            build_catalog(CHICKEN, euro_rice),
        )

    assert ("ingredients", "mixed_currencies") in reasons(error.value)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"name": "   "}, ("name", "must_not_be_blank")),
        ({"name": "x" * 256}, ("name", "too_long")),
        ({"cooking_method": "microwave"}, ("cooking_method", "unsupported_value")),
        ({"cook_time_minutes": 0}, ("cook_time_minutes", "out_of_range")),
        ({"cook_time_minutes": 601}, ("cook_time_minutes", "out_of_range")),
        ({"servings": 0}, ("servings", "out_of_range")),
        ({"servings": 13}, ("servings", "out_of_range")),
        ({"ingredients": []}, ("ingredients", "out_of_range")),
        ({"steps": []}, ("steps", "out_of_range")),
    ],
)
def test_structural_rules_are_enforced(overrides: dict, expected: tuple[str, str]) -> None:
    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(**overrides), build_catalog(CHICKEN, RICE, OLIVE_OIL)
        )

    assert expected in reasons(error.value)


@pytest.mark.parametrize(
    ("step", "reason"),
    [
        ("   ", "must_not_be_blank"),
        ("x" * 1001, "too_long"),
        ("Смотри рецепт на https://example.com", "unsafe_text"),
        ("<script>alert(1)</script>", "unsafe_text"),
    ],
)
def test_step_text_is_validated(step: str, reason: str) -> None:
    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(steps=["Обжарить курицу.", step]),
            build_catalog(CHICKEN, RICE, OLIVE_OIL),
        )

    assert ("steps.1", reason) in reasons(error.value)


def test_control_characters_are_stripped_from_text() -> None:
    recipe = build_engine().canonicalize(
        build_draft(
            name="Курица\x00 с рисом",
            steps=["Обжарить\x07 курицу."],
            description="Простой\x1f ужин",
        ),
        build_catalog(CHICKEN, RICE, OLIVE_OIL),
    )

    assert recipe.name == "Курица с рисом"
    assert recipe.steps == ["Обжарить курицу."]
    assert recipe.description == "Простой ужин"


def test_quantity_and_grams_ranges_are_enforced() -> None:
    with pytest.raises(RecipeValidationError) as too_small:
        build_engine().canonicalize(
            build_draft(
                ingredients=[
                    IngredientDraft(name="рис", quantity=Decimal("0.001"), unit="g")
                ]
            ),
            build_catalog(RICE),
        )
    with pytest.raises(RecipeValidationError) as too_many_grams:
        build_engine().canonicalize(
            build_draft(
                ingredients=[IngredientDraft(name="рис", quantity=Decimal("6"), unit="kg")]
            ),
            build_catalog(RICE),
        )

    assert ("ingredients.0.quantity", "out_of_range") in reasons(too_small.value)
    assert ("ingredients.0.quantity", "grams_out_of_range") in reasons(
        too_many_grams.value
    )


def test_fingerprint_ignores_order_and_spelling() -> None:
    engine = build_engine()
    catalog = build_catalog(CHICKEN, RICE, OLIVE_OIL)

    first = engine.canonicalize(build_draft(), catalog)
    second = engine.canonicalize(
        build_draft(
            name="  курица С Рисом  ",
            ingredients=[
                IngredientDraft(name="Рис", quantity=Decimal("100"), unit="g"),
                IngredientDraft(name="Оливковое масло", quantity=Decimal("1"), unit="tbsp"),
                IngredientDraft(name="Куриная грудка", quantity=Decimal("0.2"), unit="kg"),
            ],
        ),
        catalog,
    )

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64


@pytest.mark.parametrize(
    "overrides",
    [
        {"servings": 4},
        {"cooking_method": "bake"},
        {"name": "Курица с рисом и овощами"},
        {
            "ingredients": [
                IngredientDraft(name="куриная грудка", quantity=Decimal("210"), unit="g"),
                IngredientDraft(name="рис", quantity=Decimal("100"), unit="g"),
                IngredientDraft(name="оливковое масло", quantity=Decimal("1"), unit="tbsp"),
            ]
        },
    ],
)
def test_fingerprint_changes_with_the_dish(overrides: dict) -> None:
    engine = build_engine()
    catalog = build_catalog(CHICKEN, RICE, OLIVE_OIL)

    baseline = engine.canonicalize(build_draft(), catalog)
    changed = engine.canonicalize(build_draft(**overrides), catalog)

    assert baseline.fingerprint != changed.fingerprint


def test_servings_divide_the_nutrition_and_cost() -> None:
    engine = build_engine()
    catalog = build_catalog(CHICKEN, RICE, OLIVE_OIL)

    one_serving = engine.canonicalize(build_draft(servings=1), catalog)
    four_servings = engine.canonicalize(build_draft(servings=4), catalog)

    assert one_serving.nutrition.calories_kcal == 796
    assert four_servings.nutrition.calories_kcal == 199
    assert four_servings.estimated_cost_amount == Decimal("28.11")
    # Ingredient amounts describe the whole recipe, not one serving.
    assert one_serving.ingredients[0].quantity_g == four_servings.ingredients[0].quantity_g
