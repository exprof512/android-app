"""ImageGenerationService: enqueue, dedup, read, regenerate/retry."""

from __future__ import annotations

import logging
from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import OwnershipDenied
from app.images.errors import (
    ImageGenerationInProgress,
    ImageNotFound,
    ImageRetryNotAllowed,
)
from app.images.models import AiImageUsage, RecipeImage
from app.images.prompts import prompt_hash
from app.images.repository import ImageRepository
from app.images.schemas import RecipeImageOut
from app.recipes.models import Recipe
from app.recipes.repository import RecipeRepository
from app.storage.provider import StorageProvider
from app.workers.main import arq_redis_settings

logger = logging.getLogger(__name__)

REGENERATE_LIMIT_24H = 2


class ImageGenerationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: ImageRepository,
        recipes: RecipeRepository,
        storage: StorageProvider,
        settings: Settings,
        redis_pool: ArqRedis | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._recipes = recipes
        self._storage = storage
        self._settings = settings
        self._redis_pool = redis_pool

    async def enqueue_for_recipe(
        self,
        recipe_id: UUID,
        *,
        user_id: UUID | None = None,
        force: bool = False,
    ) -> RecipeImageOut:
        recipe = await self._recipes.get_recipe(recipe_id)
        if recipe is None or recipe.status != "ready":
            raise ImageNotFound()

        primary = await self._repository.get_primary(recipe_id)
        if primary and primary.generation_status == "ready" and not force:
            return self._to_out(primary)

        if await self._repository.has_active_job(recipe_id):
            active = await self._repository.get_primary(recipe_id)
            if active is not None:
                return self._to_out(active)
            raise ImageGenerationInProgress()

        # Dedup across recipes with the same fingerprint.
        existing = await self._repository.find_ready_by_fingerprint(
            recipe.recipe_fingerprint
        )
        hash_value = prompt_hash(
            recipe_fingerprint=recipe.recipe_fingerprint,
            model=self._settings.openai_image_model,
            output_format=self._settings.openai_image_format or "webp",
        )
        if existing is not None and not force:
            image = RecipeImage(
                recipe_id=recipe_id,
                storage_key=existing.storage_key,
                thumbnail_storage_key=existing.thumbnail_storage_key,
                width=existing.width,
                height=existing.height,
                format=existing.format,
                file_size=existing.file_size,
                model=existing.model,
                prompt_hash=hash_value,
                generation_status="ready",
                is_primary=True,
                source_image_id=existing.id,
            )
            await self._clear_primary(recipe_id)
            await self._repository.add_image(image)
            await self._repository.add_usage(
                AiImageUsage(
                    user_id=user_id,
                    recipe_id=recipe_id,
                    recipe_image_id=image.id,
                    model=existing.model or self._settings.openai_image_model,
                    status="reused",
                    estimated_cost=0,
                    retry_count=0,
                )
            )
            await self._session.commit()
            return self._to_out(image)

        await self._clear_primary(recipe_id)
        image = RecipeImage(
            recipe_id=recipe_id,
            prompt_hash=hash_value,
            generation_status="pending",
            is_primary=True,
            model=self._settings.openai_image_model,
        )
        await self._repository.add_image(image)
        await self._repository.add_usage(
            AiImageUsage(
                user_id=user_id,
                recipe_id=recipe_id,
                recipe_image_id=image.id,
                model=self._settings.openai_image_model,
                size=self._settings.openai_image_size or None,
                quality=self._settings.openai_image_quality or None,
                status="pending",
                retry_count=0,
            )
        )
        await self._session.commit()
        await self._enqueue_job(image.id)
        return self._to_out(image)

    async def get_primary_for_user(
        self, user_id: UUID, recipe_id: UUID
    ) -> RecipeImageOut:
        await self._ensure_recipe_access(user_id, recipe_id)
        image = await self._repository.get_primary(recipe_id)
        if image is None:
            # Lazy enqueue so older recipes still get photos.
            return await self.enqueue_for_recipe(recipe_id, user_id=user_id)
        return self._to_out(image)

    async def list_for_user(
        self, user_id: UUID, recipe_id: UUID
    ) -> list[RecipeImageOut]:
        await self._ensure_recipe_access(user_id, recipe_id)
        images = await self._repository.list_for_recipe(recipe_id)
        return [self._to_out(image) for image in images]

    async def regenerate(self, user_id: UUID, recipe_id: UUID) -> RecipeImageOut:
        await self._ensure_recipe_access(user_id, recipe_id)
        if await self._repository.has_active_job(recipe_id):
            raise ImageGenerationInProgress()
        count = await self._repository.count_regenerations_24h(recipe_id)
        if count >= REGENERATE_LIMIT_24H:
            raise ImageRetryNotAllowed()
        return await self.enqueue_for_recipe(
            recipe_id, user_id=user_id, force=True
        )

    async def retry(self, user_id: UUID, image_id: UUID) -> RecipeImageOut:
        image = await self._repository.get_image(image_id)
        if image is None:
            raise ImageNotFound()
        await self._ensure_recipe_access(user_id, image.recipe_id)
        if image.generation_status != "failed":
            raise ImageRetryNotAllowed()
        if image.retry_count >= self._settings.image_max_retries:
            raise ImageRetryNotAllowed()
        if await self._repository.has_active_job(image.recipe_id):
            raise ImageGenerationInProgress()
        image.generation_status = "pending"
        image.generation_error = None
        image.retry_count += 1
        await self._session.commit()
        await self._enqueue_job(image.id)
        return self._to_out(image)

    async def _enqueue_job(self, image_id: UUID) -> None:
        pool = self._redis_pool
        close_pool = False
        if pool is None:
            if self._settings.app_env == "test":
                logger.info(
                    "image_job_skipped_in_test",
                    extra={"recipe_image_id": str(image_id)},
                )
                return
            pool = await create_pool(arq_redis_settings(self._settings.redis_url))
            close_pool = True
        try:
            await pool.enqueue_job("generate_recipe_image", str(image_id))
        finally:
            if close_pool:
                await pool.aclose()

    async def _clear_primary(self, recipe_id: UUID) -> None:
        primary = await self._repository.get_primary(recipe_id)
        if primary is not None:
            primary.is_primary = False

    async def _ensure_recipe_access(self, user_id: UUID, recipe_id: UUID) -> Recipe:
        recipe = await self._recipes.get_recipe(recipe_id)
        if recipe is None or recipe.status != "ready":
            raise ImageNotFound()
        is_favorite = await self._recipes.is_favorite(user_id, recipe_id)
        in_plan = await self._recipes.user_has_recipe_in_plans(user_id, recipe_id)
        if not is_favorite and not in_plan:
            raise OwnershipDenied()
        return recipe

    def _to_out(self, image: RecipeImage) -> RecipeImageOut:
        url = None
        thumbnail_url = None
        if image.generation_status == "ready" and image.storage_key:
            url = self._storage.get_public_url(image.storage_key)
            if image.thumbnail_storage_key:
                thumbnail_url = self._storage.get_public_url(
                    image.thumbnail_storage_key
                )
        retry_allowed = (
            image.generation_status == "failed"
            and image.retry_count < self._settings.image_max_retries
        )
        return RecipeImageOut(
            id=image.id,
            recipe_id=image.recipe_id,
            status=image.generation_status,
            url=url,
            thumbnail_url=thumbnail_url,
            width=image.width,
            height=image.height,
            format=image.format,
            retry_allowed=retry_allowed,
            updated_at=image.updated_at,
        )

    async def download_variant(
        self,
        user_id: UUID,
        recipe_id: UUID,
        image_id: UUID,
        variant: str,
        storage: StorageProvider,
    ) -> tuple[bytes, str]:
        if variant not in {
            "original.webp",
            "thumbnail.webp",
            "original.jpeg",
            "thumbnail.jpeg",
        }:
            raise ImageNotFound()
        await self._ensure_recipe_access(user_id, recipe_id)
        image = await self._repository.get_image(image_id)
        if (
            image is None
            or image.recipe_id != recipe_id
            or image.generation_status != "ready"
        ):
            raise ImageNotFound()
        key = (
            image.storage_key
            if variant.startswith("original")
            else image.thumbnail_storage_key
        )
        if not key:
            raise ImageNotFound()
        data = await storage.download(key)
        return data, f"image/{image.format or 'webp'}"
