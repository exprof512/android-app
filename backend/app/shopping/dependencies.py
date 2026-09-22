"""Shopping FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.shopping.repository import ShoppingRepository
from app.shopping.service import ShoppingService


def get_shopping_service(
    session: AsyncSession = Depends(get_db_session),
) -> ShoppingService:
    return ShoppingService(session=session, repository=ShoppingRepository(session))
