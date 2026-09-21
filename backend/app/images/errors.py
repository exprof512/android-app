"""Image domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class ImageProviderError(Exception):
    def __init__(self, *, code: str, message: str, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class ImageNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="image_not_found",
            message="Изображение не найдено.",
        )


class ImageGenerationInProgress(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="image_generation_in_progress",
            message="Генерация изображения уже выполняется.",
        )


class ImageRetryNotAllowed(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=429,
            code="image_retry_not_allowed",
            message="Повторная генерация временно недоступна.",
        )
