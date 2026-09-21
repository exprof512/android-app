"""Text AI errors that map to safe API responses."""

from __future__ import annotations

from app.core.errors import ApiError


class TextAIProviderError(Exception):
    """Raised by a text provider; never carries secrets or raw prompts."""

    def __init__(self, *, code: str, message: str, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class TextAIUnavailable(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="ai_generation_unavailable",
            message="Не удалось получить ответ AI. Попробуйте позже.",
        )


class TextAIValidationFailed(ApiError):
    def __init__(self, details: list[dict[str, str]] | None = None) -> None:
        super().__init__(
            status_code=422,
            code="ai_output_invalid",
            message="AI вернул данные, которые не прошли проверку.",
            details=details,
        )
