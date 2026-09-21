"""Arq worker callable: generate → optimize → upload → persist status."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.core.db import Database
from app.images.errors import ImageProviderError
from app.images.models import AiImageUsage, RecipeImage
from app.images.optimize import optimize_pair
from app.images.prompts import build_image_prompt
from app.images.schemas import ImageGenerationRequest
from app.images.storage import original_key, thumbnail_key
from app.integrations.openai.images import OpenAIImageProvider
from app.recipes.models import Recipe
from app.storage.s3 import S3StorageProvider

logger = logging.getLogger(__name__)


async def generate_recipe_image(ctx: dict, recipe_image_id: str) -> None:
    """Background job registered on the Arq worker."""
    settings: Settings = ctx.get("settings") or get_settings()
    database: Database = ctx["database"]
    storage: S3StorageProvider = ctx["storage"]
    provider = ctx.get("image_provider") or OpenAIImageProvider(
        api_key=settings.openai_api_key,
        timeout_seconds=settings.openai_image_timeout_seconds,
    )

    image_uuid = UUID(recipe_image_id)
    async with database.sessions() as session:
        image = await session.get(RecipeImage, image_uuid)
        if image is None:
            logger.warning(
                "image_job_missing_row",
                extra={"recipe_image_id": recipe_image_id},
            )
            return
        if image.generation_status not in {"pending", "processing"}:
            return

        recipe = (
            await session.execute(
                select(Recipe)
                .where(Recipe.id == image.recipe_id)
                .options(selectinload(Recipe.ingredients))
            )
        ).scalar_one_or_none()
        if recipe is None:
            image.generation_status = "failed"
            image.generation_error = "recipe_missing"
            await session.commit()
            return

        image.generation_status = "processing"
        await _touch_usage(session, image, status="processing")
        await session.commit()

        prompt = build_image_prompt(recipe)
        request = ImageGenerationRequest(
            prompt=prompt,
            model=settings.openai_image_model,
            size=settings.openai_image_size or None,
            quality=settings.openai_image_quality or None,
            output_format=settings.openai_image_format or "webp",
        )

        try:
            result = await provider.generate(request)
            original, thumbnail = optimize_pair(
                result.content,
                output_format=settings.openai_image_format or "webp",
            )
            orig_key = original_key(recipe.id, image.id, original.format)
            thumb_key = thumbnail_key(recipe.id, image.id, thumbnail.format)
            await storage.upload(
                orig_key,
                original.content,
                content_type=f"image/{original.format}",
                cache_control="public, max-age=86400",
            )
            try:
                await storage.upload(
                    thumb_key,
                    thumbnail.content,
                    content_type=f"image/{thumbnail.format}",
                    cache_control="public, max-age=86400",
                )
            except Exception:
                await storage.delete(orig_key)
                raise

            image.storage_key = orig_key
            image.thumbnail_storage_key = thumb_key
            image.width = original.width
            image.height = original.height
            image.format = original.format
            image.file_size = original.file_size
            image.model = result.model
            image.generation_status = "ready"
            image.generation_error = None
            await _touch_usage(
                session,
                image,
                status="ready",
                duration_ms=result.duration_ms,
            )
            await session.commit()
            logger.info(
                "image_generation_ready",
                extra={
                    "recipe_id": str(recipe.id),
                    "recipe_image_id": str(image.id),
                    "image_duration_ms": result.duration_ms,
                },
            )
        except ImageProviderError as exc:
            image.generation_status = "failed"
            image.generation_error = exc.code
            await _touch_usage(
                session, image, status="failed", error_code=exc.code
            )
            await session.commit()
            if (
                exc.retryable
                and image.retry_count < settings.image_max_retries
            ):
                # Arq will not auto-retry this wrapper; service.retry is explicit.
                logger.warning(
                    "image_generation_failed",
                    extra={
                        "recipe_image_id": str(image.id),
                        "error_code": exc.code,
                    },
                )
        except Exception as exc:
            image.generation_status = "failed"
            image.generation_error = "image_processing_failed"
            await _touch_usage(
                session,
                image,
                status="failed",
                error_code="image_processing_failed",
            )
            await session.commit()
            logger.warning(
                "image_generation_failed",
                extra={
                    "recipe_image_id": str(image.id),
                    "error_code": "image_processing_failed",
                },
            )
            raise exc


async def _touch_usage(
    session,
    image: RecipeImage,
    *,
    status: str,
    duration_ms: int | None = None,
    error_code: str | None = None,
) -> None:
    statement = (
        select(AiImageUsage)
        .where(AiImageUsage.recipe_image_id == image.id)
        .order_by(AiImageUsage.created_at.desc())
        .limit(1)
    )
    usage = (await session.execute(statement)).scalar_one_or_none()
    if usage is None:
        return
    usage.status = status
    if duration_ms is not None:
        usage.duration_ms = duration_ms
    if error_code is not None:
        usage.error_code = error_code
    usage.retry_count = image.retry_count
