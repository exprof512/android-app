"""Persistence helpers for recipe images."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.images.models import AiImageUsage, RecipeImage
from app.recipes.models import Recipe


class ImageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_image(self, image_id: UUID) -> RecipeImage | None:
        return await self._session.get(RecipeImage, image_id)

    async def get_primary(self, recipe_id: UUID) -> RecipeImage | None:
        statement = select(RecipeImage).where(
            RecipeImage.recipe_id == recipe_id,
            RecipeImage.is_primary.is_(True),
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def list_for_recipe(self, recipe_id: UUID) -> list[RecipeImage]:
        statement = (
            select(RecipeImage)
            .where(RecipeImage.recipe_id == recipe_id)
            .order_by(RecipeImage.is_primary.desc(), RecipeImage.created_at.desc())
        )
        return list((await self._session.execute(statement)).scalars())

    async def find_ready_by_fingerprint(
        self, fingerprint: str
    ) -> RecipeImage | None:
        statement = (
            select(RecipeImage)
            .join(Recipe, Recipe.id == RecipeImage.recipe_id)
            .where(
                Recipe.recipe_fingerprint == fingerprint,
                RecipeImage.generation_status == "ready",
                RecipeImage.is_primary.is_(True),
            )
            .order_by(RecipeImage.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def find_ready_by_normalized_name(self, normalized_name: str) -> RecipeImage | None:
        """Reuse photos for the same dish even when grams/fingerprint differ slightly."""
        if not normalized_name:
            return None
        statement = (
            select(RecipeImage)
            .join(Recipe, Recipe.id == RecipeImage.recipe_id)
            .where(
                RecipeImage.generation_status == "ready",
                RecipeImage.is_primary.is_(True),
                RecipeImage.storage_key.is_not(None),
            )
            .order_by(RecipeImage.created_at.desc())
            .limit(50)
        )
        candidates = list((await self._session.execute(statement)).scalars())
        from app.recipes.normalization import canonical_key

        for image in candidates:
            recipe = await self._session.get(Recipe, image.recipe_id)
            if recipe is not None and canonical_key(recipe.name) == normalized_name:
                return image
        return None

    async def has_active_job(self, recipe_id: UUID) -> bool:
        statement = select(RecipeImage.id).where(
            RecipeImage.recipe_id == recipe_id,
            RecipeImage.generation_status.in_(("pending", "processing")),
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None

    async def count_regenerations_24h(self, recipe_id: UUID) -> int:
        since = datetime.now(UTC) - timedelta(hours=24)
        statement = select(func.count()).select_from(RecipeImage).where(
            and_(
                RecipeImage.recipe_id == recipe_id,
                RecipeImage.created_at >= since,
            )
        )
        return int((await self._session.execute(statement)).scalar_one())

    async def add_image(self, image: RecipeImage) -> RecipeImage:
        self._session.add(image)
        await self._session.flush()
        return image

    async def add_usage(self, usage: AiImageUsage) -> AiImageUsage:
        self._session.add(usage)
        await self._session.flush()
        return usage
