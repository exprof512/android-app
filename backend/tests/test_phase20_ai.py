"""Phase 20 Adaptive AI — context, validator, recommendations (MockTextProvider only)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.ai.cache import MemoryCacheStore, TextAICache
from app.ai.context import AIContextBuilder
from app.ai.models import AiRecommendationRecord
from app.ai.mock import MockTextProvider
from app.ai.operations import OP_FOOD_SUGGESTION, PROMPT_VERSION_BY_TEXT_OP
from app.ai.prompts import system_prompt_for
from app.ai.recommendations import RecommendationService
from app.ai.schemas import RecipeCandidate, json_schema_for
from app.ai.service import TextAIService
from app.ai.validator import AIResponseValidator
from app.ai.versions import AI_CONTEXT_SCHEMA_VERSION, SUGGESTION_PROMPT_VERSION
from app.auth.models import User
from app.auth.passwords import PasswordHasher
from app.entitlements.repository import EntitlementsRepository
from app.entitlements.service import EntitlementsService
from app.profiles.models import FoodRestriction, Goal, UserProfile
from app.recipes.engine import RecipeEngine
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from app.recipes.repository import RecipeRepository
from app.recipes.service import RecipeService

FIXTURES = Path(__file__).parent / "fixtures" / "ai"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _seed_ingredients(session) -> None:
    for name, kcal, protein, fat, carbs, price in (
        ("Куриная грудка", 165, 31, 3.6, 0, 45),
        ("Рис", 344, 7, 1, 78, 10),
        ("Брокколи", 34, 2.8, 0.4, 7, 25),
        ("Арахис", 567, 26, 49, 16, 80),
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


async def _user(session, email: str = "phase20@example.com") -> User:
    hasher = PasswordHasher()
    user = User(
        email=email,
        password_hash=hasher.hash("correct horse battery staple"),
        locale="ru-RU",
    )
    session.add(user)
    await session.flush()
    return user


def _text_ai(session, provider: MockTextProvider) -> TextAIService:
    return TextAIService(
        provider=provider,
        cache=TextAICache(MemoryCacheStore(), ttl_seconds=60, schema_version=1),
        session=session,
        model="mock-text-model",
        max_attempts=2,
        schema_version=1,
    )


def _recipe_service(session, services) -> RecipeService:
    return RecipeService(
        session=session,
        repository=RecipeRepository(session),
        engine=RecipeEngine(services.nutrition),
    )


@pytest.mark.asyncio
async def test_context_builder_sanitizes_secrets(session):
    user = await _user(session)
    session.add(
        UserProfile(
            user_id=user.id,
            meals_per_day=3,
            max_cook_time_minutes=45,
            grocery_budget_weekly=Decimal("3500"),
            currency="RUB",
        )
    )
    session.add(
        FoodRestriction(
            user_id=user.id,
            display_name="Арахис",
            normalized_food_name="арахис",
            restriction_type="allergy",
        )
    )
    await session.flush()

    ctx = await AIContextBuilder(session).build(
        user.id,
        extra={
            "email": "should-drop@example.com",
            "password": "secret",
            "jwt": "token",
            "api_key": "sk-test",
            "note": "ok",
        },
    )

    assert ctx["context_version"] == AI_CONTEXT_SCHEMA_VERSION
    assert "nutrition_policy_version" in ctx
    assert "email" not in ctx
    assert "password" not in ctx
    assert "jwt" not in ctx
    assert "api_key" not in ctx
    assert ctx["note"] == "ok"
    assert "Арахис" in ctx["restrictions"]
    assert ctx["meals_per_day"] == 3
    dumped = json.dumps(ctx)
    assert "should-drop" not in dumped
    assert "sk-test" not in dumped


@pytest.mark.asyncio
async def test_validator_fixture_matrix(session, services):
    _seed_ingredients(session)
    await session.flush()
    catalog = await RecipeRepository(session).active_catalog()
    validator = AIResponseValidator(services.nutrition)

    cases = [
        "allergy_violation.json",
        "unknown_ingredient.json",
        "cook_time.json",
        "duplicate_recent.json",
        "budget_soft.json",
    ]
    for name in cases:
        fixture = _load(name)
        candidate = RecipeCandidate.model_validate(fixture["recipe"])
        result = validator.validate_from_context(
            candidate, catalog=catalog, context=fixture["context"]
        )
        for code in fixture["expected_error_codes"]:
            assert code in result.error_codes, f"{name}: missing {code} in {result.error_codes}"
        if fixture.get("expect_ok"):
            assert result.ok
        else:
            hard = [c for c in result.error_codes if c != "budget_soft_exceeded"]
            if hard:
                assert not result.ok


@pytest.mark.asyncio
async def test_valid_suggestion_passes_validator(session, services):
    _seed_ingredients(session)
    await session.flush()
    catalog = await RecipeRepository(session).active_catalog()
    fixture = _load("valid_suggestion.json")
    candidate = RecipeCandidate.model_validate(fixture["candidates"][0]["recipe"])
    result = AIResponseValidator(services.nutrition).validate_from_context(
        candidate,
        catalog=catalog,
        context={"restrictions": [], "max_cook_time_minutes": 60},
    )
    assert result.ok
    assert result.canonical is not None
    assert result.canonical.nutrition.calories_kcal > 0


@pytest.mark.asyncio
async def test_recommendation_happy_path_and_two_step_apply(session, services):
    _seed_ingredients(session)
    user = await _user(session, "rec@example.com")
    goal = Goal(
        user_id=user.id,
        goal_type="lose_weight",
        status="active",
        calorie_target_kcal=1800,
        protein_target_g=Decimal("120"),
        fat_target_g=Decimal("60"),
        carbohydrate_target_g=Decimal("180"),
        bmr_kcal=1400,
        tdee_kcal=2000,
        safety_floor_kcal=1200,
        nutrition_policy_version="v1",
    )
    session.add(goal)
    await session.flush()
    profile = UserProfile(
        user_id=user.id,
        meals_per_day=3,
        max_cook_time_minutes=60,
        grocery_budget_weekly=Decimal("5000"),
        currency="RUB",
        active_goal_id=goal.id,
    )
    session.add(profile)
    await session.flush()

    suggestion = _load("valid_suggestion.json")
    provider = MockTextProvider([suggestion])
    entitlements = EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=services.settings,
    )
    await entitlements.ensure_free_subscription(user.id)

    service = RecommendationService(
        session=session,
        text_ai=_text_ai(session, provider),
        nutrition=services.nutrition,
        recipes=_recipe_service(session, services),
        entitlements=entitlements,
        settings=services.settings,
        ai_model="mock-text-model",
    )

    out = await service.recommend(user.id, intent="lunch", meal_type="lunch")
    assert out.candidates
    assert out.candidates[0].calories_kcal > 0
    assert out.candidates[0].recipe_id is not None
    assert len(provider.calls) == 1
    assert "prompt_version" in provider.calls[0].user_payload

    records = (
        await session.execute(select(AiRecommendationRecord))
    ).scalars().all()
    assert len(records) == 1
    assert records[0].status == "proposed"
    assert records[0].prompt_version == SUGGESTION_PROMPT_VERSION
    # No raw prompt/response body columns
    assert not hasattr(records[0], "prompt")
    assert not hasattr(records[0], "response_body")

    # Apply without recommendation_id must fail (two-step)
    with pytest.raises(Exception) as exc_info:
        await service.execute(
            user.id,
            action_type="create_nutrition_log",
            payload={
                "recipe_id": str(out.candidates[0].recipe_id),
                "meal_type": "lunch",
            },
            recommendation_id=None,
        )
    assert getattr(exc_info.value, "code", "") == "confirmation_required"

    applied = await service.apply(
        user.id,
        out.recommendation_id,
        action_type="create_nutrition_log",
        payload={
            "recipe_id": str(out.candidates[0].recipe_id),
            "meal_type": "lunch",
        },
    )
    assert applied.status == "applied"
    assert "nutrition_log_id" in applied.result

    await session.refresh(records[0])
    assert records[0].status == "selected"


@pytest.mark.asyncio
async def test_recommendation_quota(session, services):
    _seed_ingredients(session)
    user = await _user(session, "quota@example.com")
    session.add(
        UserProfile(
            user_id=user.id,
            meals_per_day=3,
            max_cook_time_minutes=60,
            currency="RUB",
        )
    )
    await session.flush()

    settings = services.settings.model_copy(
        update={"entitlement_free_ai_recommendation_per_day": 1}
    )
    entitlements = EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=settings,
    )
    await entitlements.ensure_free_subscription(user.id)

    suggestion = _load("valid_suggestion.json")
    provider = MockTextProvider([suggestion, suggestion])
    service = RecommendationService(
        session=session,
        text_ai=_text_ai(session, provider),
        nutrition=services.nutrition,
        recipes=_recipe_service(session, services),
        entitlements=entitlements,
        settings=settings,
        ai_model="mock-text-model",
    )
    await service.recommend(user.id)
    with pytest.raises(Exception) as exc_info:
        await service.recommend(user.id)
    assert getattr(exc_info.value, "code", "") == "usage_limit_exceeded"


@pytest.mark.asyncio
async def test_cache_fingerprint_includes_versions():
    cache = TextAICache(MemoryCacheStore(), ttl_seconds=60, schema_version=1)
    base = {
        "goal": "lose_weight",
        "context_version": "v2",
        "prompt_version": "2",
        "nutrition_policy_version": "v1",
    }
    fp1 = cache.fingerprint(operation=OP_FOOD_SUGGESTION, model="m", payload=base)
    fp2 = cache.fingerprint(
        operation=OP_FOOD_SUGGESTION,
        model="m",
        payload={**base, "prompt_version": "3"},
    )
    fp3 = cache.fingerprint(
        operation=OP_FOOD_SUGGESTION,
        model="m",
        payload={**base, "context_version": "v3"},
    )
    assert fp1 != fp2
    assert fp1 != fp3


def test_prompt_versions_wired():
    prompt = system_prompt_for("food_suggestion")
    assert "prompt_version=2" in prompt
    assert PROMPT_VERSION_BY_TEXT_OP["food_suggestion"] == "2"
    schema = json_schema_for("food_suggestion")
    assert schema["type"] == "object"
    assert "candidates" in schema["properties"]


@pytest.mark.asyncio
async def test_no_live_network_in_phase20(session, services):
    """Guard: MockTextProvider only; empty queue fails locally without HTTP."""
    _seed_ingredients(session)
    user = await _user(session, "nonet@example.com")
    session.add(UserProfile(user_id=user.id, meals_per_day=3, currency="RUB"))
    await session.flush()
    provider = MockTextProvider([])  # no responses, no network
    service = RecommendationService(
        session=session,
        text_ai=_text_ai(session, provider),
        nutrition=services.nutrition,
        recipes=_recipe_service(session, services),
        entitlements=None,
        settings=services.settings,
    )
    with pytest.raises(Exception):
        await service.recommend(user.id)
