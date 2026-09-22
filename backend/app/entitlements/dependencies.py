"""FastAPI wiring for entitlements."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_db_session
from app.entitlements.repository import EntitlementsRepository
from app.entitlements.service import EntitlementsService


def get_entitlements_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EntitlementsService:
    settings: Settings = request.app.state.settings
    return EntitlementsService(
        session=session,
        repository=EntitlementsRepository(session),
        settings=settings,
    )
