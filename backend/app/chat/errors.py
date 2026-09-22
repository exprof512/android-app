"""Chat domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class ConversationNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="conversation_not_found",
            message="Диалог не найден.",
        )


class ChatMessageEmpty(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="chat_message_empty",
            message="Сообщение не может быть пустым.",
        )
