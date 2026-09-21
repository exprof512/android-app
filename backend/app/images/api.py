"""Recipe image HTTP endpoints and media delivery."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.auth.dependencies import CurrentUser
from app.images.dependencies import get_image_service, get_storage
from app.images.errors import ImageNotFound
from app.images.schemas import RecipeImageOut
from app.images.service import ImageGenerationService
from app.storage.provider import StorageProvider

router = APIRouter(tags=["images"])
media_router = APIRouter(tags=["media"])


@router.get("/recipes/{recipe_id}/image", response_model=RecipeImageOut)
async def get_recipe_image(
    recipe_id: UUID,
    user: CurrentUser,
    service: ImageGenerationService = Depends(get_image_service),
) -> RecipeImageOut:
    return await service.get_primary_for_user(user.id, recipe_id)


@router.get("/recipes/{recipe_id}/images", response_model=list[RecipeImageOut])
async def list_recipe_images(
    recipe_id: UUID,
    user: CurrentUser,
    service: ImageGenerationService = Depends(get_image_service),
) -> list[RecipeImageOut]:
    return await service.list_for_user(user.id, recipe_id)


@router.post(
    "/recipes/{recipe_id}/image/regenerate",
    response_model=RecipeImageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_recipe_image(
    recipe_id: UUID,
    user: CurrentUser,
    service: ImageGenerationService = Depends(get_image_service),
) -> RecipeImageOut:
    return await service.regenerate(user.id, recipe_id)


@router.post(
    "/images/{image_id}/retry",
    response_model=RecipeImageOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_image(
    image_id: UUID,
    user: CurrentUser,
    service: ImageGenerationService = Depends(get_image_service),
) -> RecipeImageOut:
    return await service.retry(user.id, image_id)


@media_router.get("/media/recipes/{recipe_id}/{image_id}/{variant}")
async def media_recipe_image(
    recipe_id: UUID,
    image_id: UUID,
    variant: str,
    user: CurrentUser,
    service: ImageGenerationService = Depends(get_image_service),
    storage: StorageProvider = Depends(get_storage),
) -> Response:
    """Authenticated media delivery — never exposes MinIO credentials."""
    data, content_type = await service.download_variant(
        user.id, recipe_id, image_id, variant, storage
    )
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
