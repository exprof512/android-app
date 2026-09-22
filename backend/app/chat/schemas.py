"""Chat API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    context_plan_id: UUID | None = None
    context_recipe_id: UUID | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class SuggestedActionOut(BaseModel):
    type: Literal["replace_meal_item", "open_shopping_list", "explain_balance", "none"]
    label: str
    payload: dict[str, Any] | None = None


class ChatMessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    suggested_actions: list[SuggestedActionOut] = Field(default_factory=list)
    created_at: datetime


class ConversationOut(BaseModel):
    id: UUID
    title: str | None = None
    status: str
    context_plan_id: UUID | None = None
    context_recipe_id: UUID | None = None
    messages: list[ChatMessageOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Ответы приблизительны и не заменяют врача или диетолога. "
        "FoodAI не ставит диагнозы и не гарантирует результат."
    )


class ChatMessageResponse(BaseModel):
    conversation_id: UUID
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Ответы приблизительны и не заменяют врача или диетолога. "
        "FoodAI не ставит диагнозы и не гарантирует результат."
    )
