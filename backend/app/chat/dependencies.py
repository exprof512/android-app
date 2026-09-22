"""Chat FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.dependencies import get_text_ai_service
from app.ai.service import TextAIService
from app.chat.repository import ChatRepository
from app.chat.service import ChatService
from app.core.dependencies import get_db_session


def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
    text_ai: TextAIService = Depends(get_text_ai_service),
) -> ChatService:
    return ChatService(
        session=session,
        repository=ChatRepository(session),
        text_ai=text_ai,
    )
