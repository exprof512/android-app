"""Tests for ingredient alias resolution and entitlements."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.entitlements import constants
from app.entitlements.errors import PremiumRequired, UsageLimitExceeded
from app.entitlements.repository import EntitlementsRepository
from app.entitlements.service import EntitlementsService
from app.recipes.aliases import resolve_catalog_key
from app.recipes.engine import IngredientDraft
from app.recipes.errors import RecipeValidationError
from tests.test_recipe_engine import (
    CHICKEN,
    OLIVE_OIL,
    RICE,
    build_catalog,
    build_draft,
    build_engine,
    catalog_ingredient,
)


def test_alias_maps_chicken_fillet_to_breast() -> None:
    catalog = build_catalog(CHICKEN, RICE, OLIVE_OIL)
    assert resolve_catalog_key("Куриное филе", catalog) == CHICKEN.normalized_name


def test_alias_canonicalize_accepts_colloquial_names() -> None:
    tomato = catalog_ingredient(
        "Помидор",
        calories="18",
        protein="0.9",
        fat="0.2",
        carbohydrate="3.9",
        grams_per_piece="120",
    )
    oatmeal = catalog_ingredient(
        "Овсяные хлопья",
        calories="366",
        protein="12",
        fat="7",
        carbohydrate="62",
    )
    catalog = build_catalog(CHICKEN, tomato, oatmeal, OLIVE_OIL)
    recipe = build_engine().canonicalize(
        build_draft(
            ingredients=[
                IngredientDraft(name="куриное филе", quantity=Decimal("150"), unit="g"),
                IngredientDraft(name="томаты", quantity=Decimal("2"), unit="piece"),
                IngredientDraft(name="овсянка", quantity=Decimal("40"), unit="g"),
            ],
        ),
        catalog,
    )
    names = {item.display_name for item in recipe.ingredients}
    assert "Куриная грудка" in names
    assert "Помидор" in names
    assert "Овсяные хлопья" in names


def test_truly_unknown_ingredient_still_rejected() -> None:
    with pytest.raises(RecipeValidationError) as error:
        build_engine().canonicalize(
            build_draft(
                ingredients=[
                    IngredientDraft(
                        name="драконий перец", quantity=Decimal("10"), unit="g"
                    )
                ],
            ),
            build_catalog(CHICKEN),
        )
    assert ("ingredients.0.name", "unknown_ingredient") in [
        (d["field"], d["reason"]) for d in error.value.details
    ]


@pytest.mark.asyncio
async def test_entitlements_free_limits_and_premium(
    session, test_settings: Settings
) -> None:
    from app.auth.models import User
    from app.auth.passwords import PasswordHasher

    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash=PasswordHasher().hash("Password123!"),
        locale="ru-RU",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    service = EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=test_settings,
    )
    await service.ensure_free_subscription(user.id)
    assert await service.get_tier(user.id) == constants.TIER_FREE

    for _ in range(test_settings.entitlement_free_meal_plan_per_day):
        await service.consume(user.id, constants.FEATURE_MEAL_PLAN_GENERATE)

    with pytest.raises(UsageLimitExceeded):
        await service.consume(user.id, constants.FEATURE_MEAL_PLAN_GENERATE)

    with pytest.raises(PremiumRequired):
        await service.consume(user.id, constants.FEATURE_IMAGE_REGENERATE)
