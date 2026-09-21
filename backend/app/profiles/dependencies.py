"""Profile dependency wiring."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_services
from app.core.services import Services
from app.profiles.repository import ProfileRepository
from app.profiles.service import ProfileService


def get_profile_service(
    session: AsyncSession = Depends(get_db_session),
    services: Services = Depends(get_services),
) -> ProfileService:
    return ProfileService(
        session=session,
        repository=ProfileRepository(session),
        nutrition=services.nutrition,
    )
