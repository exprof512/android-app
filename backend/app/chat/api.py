"""Contextual chat HTTP endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import CurrentUser
from app.chat.dependencies import get_chat_service
from app.chat.schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationOut,
)
from app.chat.service import ChatService

router = APIRouter(prefix="/ai/chat", tags=["chat"])


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    user: CurrentUser,
    service: ChatService = Depends(get_chat_service),
) -> ConversationOut:
    return await service.create_or_get(user.id, payload)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str,
    user: CurrentUser,
    service: ChatService = Depends(get_chat_service),
) -> ConversationOut:
    return await service.get(user.id, UUID(conversation_id))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
)
async def post_message(
    conversation_id: str,
    payload: ChatMessageCreate,
    user: CurrentUser,
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    return await service.post_message(user.id, UUID(conversation_id), payload)
