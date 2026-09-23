"""Phase 5 Text AI service tests — MockTextProvider only, never OpenAI."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.ai.cache import MemoryCacheStore, TextAICache
from app.ai.drafts import recipe_candidate_to_draft
from app.ai.errors import TextAIProviderError, TextAIUnavailable, TextAIValidationFailed
from app.ai.mock import MockTextProvider
from app.ai.models import AiTextUsage
from app.ai.schemas import RecipeCandidatesResponse, json_schema_for
from app.ai.service import TextAIService
from app.recipes.engine import RecipeEngine
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from app.recipes.repository import RecipeRepository

VALID_RECIPE_PAYLOAD = {
    "recipes": [
        {
            "name": "Курица с рисом и брокколи",
            "description": "Простой обед",
            "servings": 2,
            "cooking_method": "stew",
            "cook_time_minutes": 35,
            "ingredients": [
                {"name": "Куриная грудка", "quantity": 200, "unit": "g"},
                {"name": "Рис", "quantity": 150, "unit": "g"},
                {"name": "Брокколи", "quantity": 100, "unit": "g"},
            ],
            "steps": [
                "Обжарьте курицу.",
                "Добавьте рис и воду.",
                "Добавьте брокколи и тушите.",
            ],
            "rationale": "Белковый обед",
        }
    ]
}


def _service(session, provider: MockTextProvider) -> TextAIService:
    return TextAIService(
        provider=provider,
        cache=TextAICache(MemoryCacheStore(), ttl_seconds=60, schema_version=1),
        session=session,
        model="mock-text-model",
        max_attempts=2,
        schema_version=1,
    )


@pytest.mark.asyncio
async def test_generate_recipe_candidates_happy_path(session):
    provider = MockTextProvider([VALID_RECIPE_PAYLOAD])
    service = _service(session, provider)

    result = await service.generate_recipe_candidates(
        context={"goal": "lose_weight", "meals_per_day": 3}
    )

    assert isinstance(result, RecipeCandidatesResponse)
    assert result.recipes[0].name.startswith("Курица")
    assert len(provider.calls) == 1
    usage = (await session.execute(select(AiTextUsage))).scalars().all()
    assert len(usage) == 1
    assert usage[0].status == "ok"
    assert usage[0].operation == "generate_recipe_candidates"


@pytest.mark.asyncio
async def test_schema_repair_retry_then_success(session):
    provider = MockTextProvider(
        [
            {"recipes": []},  # invalid: min_length=1
            VALID_RECIPE_PAYLOAD,
        ]
    )
    service = _service(session, provider)

    result = await service.generate_recipe_candidates(context={"locale": "ru-RU"})

    assert result.recipes[0].cook_time_minutes == 35
    assert len(provider.calls) == 2
    assert "validation_feedback" in provider.calls[1].user_payload
    statuses = [
        row.status
        for row in (await session.execute(select(AiTextUsage))).scalars().all()
    ]
    assert statuses == ["invalid", "ok"]


@pytest.mark.asyncio
async def test_malformed_json_exhausts_attempts(session):
    provider = MockTextProvider(["not-json", "{broken"])
    service = _service(session, provider)

    with pytest.raises(TextAIUnavailable):
        await service.generate_recipe_candidates(context={"x": 1})

    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_provider_timeout_maps_to_unavailable(session):
    provider = MockTextProvider(
        [
            TextAIProviderError(
                code="ai_provider_timeout",
                message="timeout",
                retryable=True,
            ),
            TextAIProviderError(
                code="ai_provider_timeout",
                message="timeout",
                retryable=True,
            ),
        ]
    )
    service = _service(session, provider)

    with pytest.raises(TextAIUnavailable):
        await service.generate_recipe_candidates(context={"x": 1})


@pytest.mark.asyncio
async def test_cache_hit_skips_provider(session):
    provider = MockTextProvider([VALID_RECIPE_PAYLOAD])
    service = _service(session, provider)
    context = {"budget": 5000}

    first = await service.generate_recipe_candidates(context=context)
    second = await service.generate_recipe_candidates(context=context)

    assert first.recipes[0].name == second.recipes[0].name
    assert len(provider.calls) == 1
    statuses = [
        row.status
        for row in (await session.execute(select(AiTextUsage))).scalars().all()
    ]
    assert statuses == ["ok", "cached"]


@pytest.mark.asyncio
async def test_chat_answer_safe_refusal_shape(session):
    provider = MockTextProvider(
        [
            {
                "answer": (
                    "Я не ставлю медицинских диагнозов. Обратитесь к врачу. "
                    "Могу помочь с заменой ужина в рамках вашего плана."
                ),
                "suggested_actions": [
                    {"type": "replace_meal_item", "label": "Заменить ужин", "payload": None}
                ],
                "warnings": ["Не является медицинской консультацией."],
            }
        ]
    )
    service = _service(session, provider)

    answer = await service.chat_answer(
        context={"message": "У меня диабет, поставь диагноз"}
    )

    assert "диагноз" not in answer.answer.lower() or "не ставлю" in answer.answer.lower()
    assert answer.suggested_actions[0].type == "replace_meal_item"


@pytest.mark.asyncio
async def test_candidate_feeds_recipe_engine(session, services):
    """AI candidate becomes a RecipeDraft; NutritionEngine owns final macros."""
    from dataclasses import replace
    from decimal import Decimal

    for name, kcal, protein, fat, carbs, price in (
        ("Куриная грудка", 165, 31, 3.6, 0, 45),
        ("Рис", 344, 7, 1, 78, 10),
        ("Брокколи", 34, 2.8, 0.4, 7, 25),
    ):
        session.add(
            Ingredient(
                canonical_name=name,
                normalized_name=canonical_key(name),
                default_unit="g",
                calories_per_100g=Decimal(str(kcal)),
                protein_per_100g=Decimal(str(protein)),
                fat_per_100g=Decimal(str(fat)),
                carbohydrate_per_100g=Decimal(str(carbs)),
                reference_price_per_100g=Decimal(str(price)),
                currency="RUB",
                source="seed",
                is_active=True,
            )
        )
    await session.flush()

    provider = MockTextProvider([VALID_RECIPE_PAYLOAD])
    service = _service(session, provider)
    candidates = await service.generate_recipe_candidates(context={"locale": "ru-RU"})
    draft = recipe_candidate_to_draft(candidates.recipes[0], ai_model="mock-text-model")
    draft_with_claim = replace(draft, claimed_calories_kcal=1)

    repository = RecipeRepository(session)
    catalog = await repository.catalog_for_names(
        item.name for item in draft_with_claim.ingredients
    )
    canonical = RecipeEngine(services.nutrition).canonicalize(draft_with_claim, catalog)

    assert canonical.nutrition.calories_kcal != 1
    assert canonical.nutrition.calories_kcal > 100
    assert any("калорийности" in warning for warning in canonical.warnings)


def test_json_schema_is_object_without_open_refs():
    schema = json_schema_for("generate_recipe_candidates")
    assert schema["type"] == "object"
    assert "recipes" in schema["properties"]
    dumped = str(schema)
    assert "$ref" not in dumped


def test_json_schema_openai_strict_requires_all_properties():
    schema = json_schema_for("generate_meal_plan_proposal")
    recipe = schema["properties"]["recipes"]["items"]
    assert set(recipe["required"]) == set(recipe["properties"].keys())
    assert "description" in recipe["required"]
    assert "rationale" in recipe["required"]
    assert "default" not in recipe["properties"]["description"]
    assert recipe.get("additionalProperties") is False
