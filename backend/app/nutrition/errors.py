"""Nutrition validation errors."""

from __future__ import annotations

from app.core.errors import ApiError


class NutritionValidationError(ApiError):
    """Raised for goal data the engine refuses to turn into a target."""

    def __init__(self, details: list[dict[str, str]]) -> None:
        super().__init__(
            status_code=422,
            code="nutrition_validation_error",
            message="Проверьте значения профиля и цели.",
            details=details,
        )
