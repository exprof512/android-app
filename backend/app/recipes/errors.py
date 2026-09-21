"""Recipe domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class RecipeValidationError(ApiError):
    """Raised when a recipe candidate cannot become a canonical recipe."""

    def __init__(self, details: list[dict[str, str]]) -> None:
        super().__init__(
            status_code=422,
            code="recipe_validation_error",
            message="Рецепт не прошёл проверку.",
            details=details,
        )


class RecipeNotFound(ApiError):
    """Missing recipe and a recipe the user has no link to look the same."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="recipe_not_found",
            message="Рецепт не найден.",
        )
