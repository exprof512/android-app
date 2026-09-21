"""Meal plan domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class MealPlanNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="meal_plan_not_found",
            message="План питания не найден.",
        )


class MealPlanItemNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="meal_plan_item_not_found",
            message="Элемент плана не найден.",
        )


class ProfileIncomplete(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="profile_incomplete",
            message="Заполните профиль и цель перед генерацией плана.",
        )


class PlanConstraintsUnsatisfied(ApiError):
    def __init__(self, details: list[dict[str, str]] | None = None) -> None:
        super().__init__(
            status_code=422,
            code="plan_constraints_unsatisfied",
            message="Предложенный план не проходит проверки питания.",
            details=details,
        )
