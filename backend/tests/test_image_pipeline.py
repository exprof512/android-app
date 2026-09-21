"""Phase 7 image pipeline unit tests — MockImageProvider only."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.images.generator import generate_recipe_image
from app.images.mock import MockImageProvider
from app.images.models import RecipeImage
from app.images.optimize import optimize_pair
from app.images.prompts import prompt_hash
from app.images.repository import ImageRepository
from app.images.service import ImageGenerationService
from app.recipes.engine import IngredientDraft, RecipeDraft, RecipeEngine
from app.recipes.models import Ingredient
from app.recipes.normalization import canonical_key
from app.recipes.repository import RecipeRepository
from app.recipes.service import RecipeService
from app.storage.memory import MemoryStorageProvider
from tests.conftest import TEST_JWT_SECRET


async def _seed_and_recipe(session: AsyncSession, services) -> object:
    from sqlalchemy import select

    for name, kcal, p, f, c, price in (
        ("Куриная грудка", 165, 31, 3.6, 0, 45),
        ("Рис", 344, 7, 1, 78, 10),
        ("Брокколи", 34, 2.8, 0.4, 7, 25),
    ):
        key = canonical_key(name)
        exists = (
            await session.execute(
                select(Ingredient).where(Ingredient.normalized_name == key)
            )
        ).scalar_one_or_none()
        if exists:
            continue
        session.add(
            Ingredient(
                canonical_name=name,
                normalized_name=key,
                default_unit="g",
                calories_per_100g=Decimal(str(kcal)),
                protein_per_100g=Decimal(str(p)),
                fat_per_100g=Decimal(str(f)),
                carbohydrate_per_100g=Decimal(str(c)),
                reference_price_per_100g=Decimal(str(price)),
                currency="RUB",
                source="seed",
                is_active=True,
            )
        )
    await session.flush()
    draft = RecipeDraft(
        name="Курица с рисом",
        servings=1,
        cooking_method="stew",
        cook_time_minutes=30,
        ingredients=[
            IngredientDraft("Куриная грудка", Decimal("150"), "g"),
            IngredientDraft("Рис", Decimal("80"), "g"),
            IngredientDraft("Брокколи", Decimal("100"), "g"),
        ],
        steps=["Обжарьте.", "Добавьте рис.", "Добавьте брокколи."],
        ai_model="test",
    )
    service = RecipeService(
        session=session,
        repository=RecipeRepository(session),
        engine=RecipeEngine(services.nutrition),
    )
    stored = await service.create_recipe(draft)
    return stored.recipe


@pytest.mark.asyncio
async def test_optimize_creates_webp_pair():
    from app.images.mock import _tiny_png

    original, thumb = optimize_pair(_tiny_png(), output_format="webp")
    assert original.format == "webp"
    assert thumb.format == "webp"
    assert thumb.width <= original.width
    assert original.file_size > 0


@pytest.mark.asyncio
async def test_enqueue_dedup_and_generator(session, services, test_settings):
    recipe = await _seed_and_recipe(session, services)
    storage = MemoryStorageProvider()
    settings = Settings(
        app_env="test",
        api_prefix="/api/v1",
        database_url=test_settings.database_url,
        redis_url=test_settings.redis_url,
        jwt_secret=TEST_JWT_SECRET,
        openai_image_model="mock-image",
        openai_image_format="webp",
        image_max_retries=3,
        media_public_base_url="http://testserver/media",
    )
    service = ImageGenerationService(
        session=session,
        repository=ImageRepository(session),
        recipes=RecipeRepository(session),
        storage=storage,
        settings=settings,
    )
    first = await service.enqueue_for_recipe(recipe.id, user_id=None)
    assert first.status == "pending"

    provider = MockImageProvider()
    await generate_recipe_image(
        {
            "settings": settings,
            "database": services.database,
            "storage": storage,
            "image_provider": provider,
        },
        str(first.id),
    )
    image = await session.get(RecipeImage, first.id)
    assert image is not None
    await session.refresh(image)
    assert image.generation_status == "ready"
    assert image.storage_key is not None
    assert await storage.download(image.storage_key)

    # Re-enqueue must reuse ready primary without another provider call.
    second = await service.enqueue_for_recipe(recipe.id, user_id=None)
    assert second.status == "ready"
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_provider_failure_leaves_recipe_usable(session, services, test_settings):
    recipe = await _seed_and_recipe(session, services)
    storage = MemoryStorageProvider()
    settings = Settings(
        app_env="test",
        api_prefix="/api/v1",
        database_url=test_settings.database_url,
        redis_url=test_settings.redis_url,
        jwt_secret=TEST_JWT_SECRET,
        openai_image_model="mock-image",
        openai_image_format="webp",
        image_max_retries=3,
        media_public_base_url="http://testserver/media",
    )
    service = ImageGenerationService(
        session=session,
        repository=ImageRepository(session),
        recipes=RecipeRepository(session),
        storage=storage,
        settings=settings,
    )
    pending = await service.enqueue_for_recipe(recipe.id)
    await generate_recipe_image(
        {
            "settings": settings,
            "database": services.database,
            "storage": storage,
            "image_provider": MockImageProvider(fail_times=1),
        },
        str(pending.id),
    )
    image = await session.get(RecipeImage, pending.id)
    assert image is not None
    assert image.generation_status == "failed"
    # Recipe itself remains ready.
    assert recipe.status == "ready"


def test_prompt_hash_stable():
    a = prompt_hash(
        recipe_fingerprint="abc", model="gpt-image-2", output_format="webp"
    )
    b = prompt_hash(
        recipe_fingerprint="abc", model="gpt-image-2", output_format="webp"
    )
    assert a == b
    assert a != prompt_hash(
        recipe_fingerprint="xyz", model="gpt-image-2", output_format="webp"
    )
