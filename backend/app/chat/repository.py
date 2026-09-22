"""Chat persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chat.models import AiConversation, AiMessage


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_conversation(self, conversation: AiConversation) -> AiConversation:
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get(self, conversation_id: UUID) -> AiConversation | None:
        statement = (
            select(AiConversation)
            .where(AiConversation.id == conversation_id)
            .options(selectinload(AiConversation.messages))
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_current(self, user_id: UUID) -> AiConversation | None:
        statement = (
            select(AiConversation)
            .where(
                AiConversation.user_id == user_id,
                AiConversation.status == "active",
            )
            .options(selectinload(AiConversation.messages))
            .order_by(AiConversation.updated_at.desc())
            .limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def add_message(self, message: AiMessage) -> AiMessage:
        self._session.add(message)
        await self._session.flush()
        return message
