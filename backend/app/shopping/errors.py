"""Shopping domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class ShoppingListNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="shopping_list_not_found",
            message="Список покупок не найден.",
        )


class ShoppingItemNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="shopping_item_not_found",
            message="Позиция списка покупок не найдена.",
        )
