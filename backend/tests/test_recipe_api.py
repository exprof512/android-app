from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.services import Services
from app.recipes.engine import IngredientDraft, RecipeDraft, RecipeEngine
from app.recipes.errors import RecipeValidationError
from app.recipes.models import Ingredient, Recipe, RecipeIngredient, UserRecipeFavorite
from app.recipes.repository import RecipeRepository
from app.recipes.schemas import IngredientSubstitutionApplyRequest
from app.recipes.service import RecipeService
from tests.conftest import API_PREFIX, TEST_PASSWORD

SEED = (
    ("Куриная грудка", "куриная грудка", "g", "165", "31", "3.6", "0", "45", None, None),
    ("Рис", "рис", "g", "344", "7", "1", "78", "10", None, None),
    ("Оливковое масло", "оливковое масло", "ml", "884", "0", "100", "0", "90", None, "0.92"),
    ("Яйцо", "яйцо", "piece", "157", "13", "11", "1.1", "12", "55", None),
)

DRAFT = RecipeDraft(
    name="Курица с рисом",
    servings=2,
    cooking_method="fry",
    cook_time_minutes=30,
    ingredients=[
        IngredientDraft(name="куриная грудка", quantity=Decimal("200"), unit="g"),
        IngredientDraft(name="рис", quantity=Decimal("100"), unit="g"),
        IngredientDraft(name="оливковое масло", quantity=Decimal("1"), unit="tbsp"),
    ],
    steps=["Обжарить курицу.", "Отварить рис.", "Смешать и подать."],
    description="Простой ужин на двоих",
    ai_model="test-model",
)


@pytest_asyncio.fixture
async def catalog(session: AsyncSession) -> list[Ingredient]:
    ingredients = [
        Ingredient(
            canonical_name=canonical_name,
            normalized_name=normalized_name,
            default_unit=unit,
            calories_per_100g=Decimal(calories),
            protein_per_100g=Decimal(protein),
            fat_per_100g=Decimal(fat),
            carbohydrate_per_100g=Decimal(carbohydrate),
            reference_price_per_100g=None if price is None else Decimal(price),
            currency=None if price is None else "RUB",
            grams_per_piece=None if piece is None else Decimal(piece),
            density_g_per_ml=None if density is None else Decimal(density),
            source="seed",
            is_active=True,
        )
        for (
            canonical_name,
            normalized_name,
            unit,
            calories,
            protein,
            fat,
            carbohydrate,
            price,
            piece,
            density,
        ) in SEED
    ]
    session.add_all(ingredients)
    await session.commit()
    return ingredients


@pytest.fixture
def recipe_service(session: AsyncSession, services: Services) -> RecipeService:
    return RecipeService(
        session=session,
        repository=RecipeRepository(session),
        engine=RecipeEngine(services.nutrition),
    )


@pytest_asyncio.fixture
async def recipe(
    catalog: list[Ingredient], recipe_service: RecipeService
) -> Recipe:
    stored = await recipe_service.create_recipe(DRAFT)
    return stored.recipe


async def register(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_persisted_recipe_holds_backend_numbers(
    recipe: Recipe, session: AsyncSession
) -> None:
    stored = (await session.execute(select(Recipe))).scalar_one()

    assert stored.id == recipe.id
    assert stored.status == "ready"
    assert stored.calories_kcal == 398
    assert stored.protein_g == Decimal("34.50")
    assert stored.fat_g == Decimal("11.00")
    assert stored.carbohydrate_g == Decimal("39.00")
    assert stored.estimated_cost_amount == Decimal("56.21")
    assert stored.currency == "RUB"
    assert stored.steps == ["Обжарить курицу.", "Отварить рис.", "Смешать и подать."]
    assert stored.ai_model == "test-model"
    assert len(stored.recipe_fingerprint) == 64

    items = list(
        (
            await session.execute(
                select(RecipeIngredient).order_by(RecipeIngredient.sort_order)
            )
        ).scalars()
    )
    assert [item.quantity_g for item in items] == [
        Decimal("200.00"),
        Decimal("100.00"),
        Decimal("13.80"),
    ]
    assert [item.unit for item in items] == ["g", "g", "tbsp"]
    assert [item.cost_amount for item in items] == [
        Decimal("90.00"),
        Decimal("10.00"),
        Decimal("12.42"),
    ]


async def test_identical_draft_reuses_the_stored_recipe(
    catalog: list[Ingredient], recipe_service: RecipeService, session: AsyncSession
) -> None:
    first = await recipe_service.create_recipe(DRAFT)
    second = await recipe_service.create_recipe(DRAFT)

    assert first.reused is False
    assert second.reused is True
    assert second.recipe.id == first.recipe.id
    assert any("переиспользован" in warning for warning in second.warnings)
    assert await session.scalar(select(func.count()).select_from(Recipe)) == 1


async def test_a_rejected_draft_persists_nothing(
    catalog: list[Ingredient], recipe_service: RecipeService, session: AsyncSession
) -> None:
    draft = RecipeDraft(
        name="Неизвестное блюдо",
        servings=2,
        cooking_method="fry",
        cook_time_minutes=20,
        ingredients=[
            IngredientDraft(name="драконий перец", quantity=Decimal("10"), unit="g")
        ],
        steps=["Готовить."],
    )

    with pytest.raises(RecipeValidationError):
        await recipe_service.create_recipe(draft)

    assert await session.scalar(select(func.count()).select_from(Recipe)) == 0
    assert await session.scalar(select(func.count()).select_from(RecipeIngredient)) == 0


async def test_dish_card_needs_a_link_to_the_user(
    client: AsyncClient, recipe: Recipe
) -> None:
    tokens = await register(client, "anna@example.com")

    response = await client.get(f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(tokens))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "recipe_not_found"


async def test_favorite_opens_the_dish_card(client: AsyncClient, recipe: Recipe) -> None:
    tokens = await register(client, "anna@example.com")

    favorited = await client.post(
        f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens)
    )
    response = await client.get(f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(tokens))

    assert favorited.status_code == 204
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(recipe.id)
    assert body["name"] == "Курица с рисом"
    assert body["description"] == "Простой ужин на двоих"
    assert body["cooking_method"] == "fry"
    assert body["cook_time_minutes"] == 30
    assert body["servings"] == 2
    assert body["is_favorite"] is True
    assert body["nutrition_per_serving"] == {
        "calories_kcal": 398,
        "protein_g": 34.5,
        "fat_g": 11.0,
        "carbohydrate_g": 39.0,
    }
    assert body["estimated_cost_per_serving"] == {"amount": 56.21, "currency": "RUB"}
    assert body["ingredients"][0] == {
        "name": "Куриная грудка",
        "grams": 200.0,
        "quantity": 200.0,
        "unit": "g",
        "cost": 90.0,
    }
    assert body["steps"] == ["Обжарить курицу.", "Отварить рис.", "Смешать и подать."]


async def test_favorite_is_idempotent(
    client: AsyncClient, recipe: Recipe, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")

    first = await client.post(
        f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens)
    )
    second = await client.post(
        f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens)
    )

    assert first.status_code == second.status_code == 204
    assert await session.scalar(select(func.count()).select_from(UserRecipeFavorite)) == 1


async def test_removing_a_favorite_closes_access(
    client: AsyncClient, recipe: Recipe
) -> None:
    tokens = await register(client, "anna@example.com")
    await client.post(f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens))

    removed = await client.delete(
        f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens)
    )
    again = await client.delete(
        f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens)
    )
    card = await client.get(f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(tokens))

    assert removed.status_code == 204
    assert again.status_code == 204
    assert card.status_code == 404


async def test_favorites_are_private_to_their_owner(
    client: AsyncClient, recipe: Recipe, session: AsyncSession
) -> None:
    anna = await register(client, "anna@example.com")
    boris = await register(client, "boris@example.com")
    await client.post(f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(anna))

    boris_card = await client.get(
        f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(boris)
    )
    await client.delete(f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(boris))
    anna_card = await client.get(f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(anna))

    assert boris_card.status_code == 404
    assert anna_card.status_code == 200
    assert await session.scalar(select(func.count()).select_from(UserRecipeFavorite)) == 1


async def test_unknown_recipe_is_not_found(client: AsyncClient) -> None:
    tokens = await register(client, "anna@example.com")
    missing = uuid4()

    read = await client.get(f"{API_PREFIX}/recipes/{missing}", headers=auth(tokens))
    favorite = await client.post(
        f"{API_PREFIX}/recipes/{missing}/favorite", headers=auth(tokens)
    )

    assert read.status_code == favorite.status_code == 404
    assert favorite.json()["error"]["code"] == "recipe_not_found"


async def test_archived_recipe_is_hidden(
    client: AsyncClient, recipe: Recipe, session: AsyncSession
) -> None:
    tokens = await register(client, "anna@example.com")
    await client.post(f"{API_PREFIX}/recipes/{recipe.id}/favorite", headers=auth(tokens))
    stored = (await session.execute(select(Recipe))).scalar_one()
    stored.status = "archived"
    await session.commit()

    response = await client.get(f"{API_PREFIX}/recipes/{recipe.id}", headers=auth(tokens))

    assert response.status_code == 404


async def test_recipe_endpoints_require_authentication(
    client: AsyncClient, recipe: Recipe
) -> None:
    read = await client.get(f"{API_PREFIX}/recipes/{recipe.id}")
    favorite = await client.post(f"{API_PREFIX}/recipes/{recipe.id}/favorite")
    unfavorite = await client.delete(f"{API_PREFIX}/recipes/{recipe.id}/favorite")

    assert read.status_code == favorite.status_code == unfavorite.status_code == 401
    assert read.json()["error"]["code"] == "invalid_token"


async def test_invalid_recipe_id_uses_the_validation_envelope(
    client: AsyncClient,
) -> None:
    tokens = await register(client, "anna@example.com")

    response = await client.get(f"{API_PREFIX}/recipes/not-a-uuid", headers=auth(tokens))

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["field"] == "recipe_id"


async def test_recipe_ids_are_uuids(recipe: Recipe) -> None:
    assert isinstance(recipe.id, UUID)


async def _user_by_email(session: AsyncSession, email: str) -> User:
    return (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one()


@pytest.mark.asyncio
async def test_substitution_copy_is_reused_between_users(
    catalog,
    recipe: Recipe,
    recipe_service: RecipeService,
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    await register(client, "sub-a@example.com")
    await register(client, "sub-b@example.com")
    user_a = await _user_by_email(session, "sub-a@example.com")
    user_b = await _user_by_email(session, "sub-b@example.com")

    session.add(UserRecipeFavorite(user_id=user_a.id, recipe_id=recipe.id))
    await session.commit()

    payload = IngredientSubstitutionApplyRequest(
        original_name="Рис", replacement_name="Куриная грудка"
    )
    first = await recipe_service.apply_substitution(user_a.id, recipe.id, payload)
    assert first.id != recipe.id
    assert first.created_by_user_id == user_a.id
    assert any(
        item.display_name == "Куриная грудка" for item in first.ingredients
    )

    session.add(UserRecipeFavorite(user_id=user_b.id, recipe_id=recipe.id))
    await session.commit()
    second = await recipe_service.apply_substitution(user_b.id, recipe.id, payload)

    assert second.id == first.id
