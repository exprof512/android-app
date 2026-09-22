"""Progress FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.progress.repository import ProgressRepository
from app.progress.service import ProgressService


def get_progress_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProgressService:
    return ProgressService(session=session, repository=ProgressRepository(session))
