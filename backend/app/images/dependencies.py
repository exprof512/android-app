"""Image FastAPI dependencies and storage wiring."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_db_session, get_services
from app.core.services import Services
from app.images.repository import ImageRepository
from app.images.service import ImageGenerationService
from app.recipes.repository import RecipeRepository
from app.storage.memory import MemoryStorageProvider
from app.storage.provider import StorageProvider
from app.storage.s3 import S3StorageProvider


def get_storage(request: Request) -> StorageProvider:
    storage = getattr(request.app.state, "storage", None)
    if storage is not None:
        return storage
    services: Services = request.app.state.services
    if services.storage is not None:
        return services.storage
    settings: Settings = request.app.state.settings
    if settings.app_env == "test":
        storage = MemoryStorageProvider(
            public_base_url=settings.media_public_base_url
        )
        request.app.state.storage = storage
        return storage
    raise RuntimeError("Storage provider is not initialized.")


def get_image_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    storage: StorageProvider = Depends(get_storage),
) -> ImageGenerationService:
    settings: Settings = request.app.state.settings
    return ImageGenerationService(
        session=session,
        repository=ImageRepository(session),
        recipes=RecipeRepository(session),
        storage=storage,
        settings=settings,
        redis_pool=getattr(request.app.state, "arq_pool", None),
    )
