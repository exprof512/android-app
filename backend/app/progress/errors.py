"""Progress domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class WeightEntryNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="weight_entry_not_found",
            message="Запись веса не найдена.",
        )
