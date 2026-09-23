"""Nutrition diary service — backend-authoritative macros."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, OwnershipDenied
from app.meal_plans.models import MealPlanItem
from app.nutrition.models import NutritionLog
from app.recipes.models import Recipe


class NutritionLogValidationError(ApiError):
    def __init__(self, message: str, *, details: list[dict[str, str]] | None = None) -> None:
        super().__init__(
            status_code=422,
            code="nutrition_log_validation_error",
            message=message,
            details=details,
        )


class NutritionLogNotFound(ApiError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="nutrition_log_not_found",
            message="Запись дневника не найдена.",
        )


class NutritionDiaryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_logs(
        self, user_id: UUID, *, logged_on: date | None = None
    ) -> list[NutritionLog]:
        statement = select(NutritionLog).where(NutritionLog.user_id == user_id)
        if logged_on is not None:
            statement = statement.where(NutritionLog.logged_on == logged_on)
        statement = statement.order_by(NutritionLog.created_at.desc())
        return list((await self._session.execute(statement)).scalars())

    async def create(
        self,
        user_id: UUID,
        *,
        logged_on: date,
        meal_type: str,
        source: str,
        description: str | None = None,
        recipe_id: UUID | None = None,
        meal_plan_item_id: UUID | None = None,
        calories_kcal: int | None = None,
        protein_g: Decimal | None = None,
        fat_g: Decimal | None = None,
        carbohydrate_g: Decimal | None = None,
        servings: Decimal = Decimal("1"),
    ) -> NutritionLog:
        if meal_type not in {"breakfast", "lunch", "dinner", "snack"}:
            raise NutritionLogValidationError("Некорректный meal_type.")
        if source not in {"meal_plan_item", "recipe", "manual"}:
            raise NutritionLogValidationError("Некорректный source.")

        desc = (description or "").strip()
        cal = calories_kcal
        protein = protein_g
        fat = fat_g
        carbs = carbohydrate_g

        if source == "meal_plan_item":
            if meal_plan_item_id is None:
                raise NutritionLogValidationError("meal_plan_item_id обязателен.")
            item = await self._session.get(MealPlanItem, meal_plan_item_id)
            if item is None:
                raise NutritionLogValidationError("Приём пищи не найден.")
            from app.meal_plans.models import MealPlan

            plan_row = await self._session.get(MealPlan, item.meal_plan_id)
            if plan_row is None or plan_row.user_id != user_id:
                raise OwnershipDenied()
            cal = item.calories_kcal
            protein = item.protein_g
            fat = item.fat_g
            carbs = item.carbohydrate_g
            servings = item.servings
            recipe_id = item.recipe_id
            recipe = await self._session.get(Recipe, item.recipe_id)
            desc = desc or (recipe.name if recipe else item.meal_type)
        elif source == "recipe":
            if recipe_id is None:
                raise NutritionLogValidationError("recipe_id обязателен.")
            recipe = await self._session.get(Recipe, recipe_id)
            if recipe is None:
                raise NutritionLogValidationError("Рецепт не найден.")
            factor = Decimal(str(servings))
            cal = int(Decimal(recipe.calories_kcal) * factor)
            protein = (recipe.protein_g * factor).quantize(Decimal("0.01"))
            fat = (recipe.fat_g * factor).quantize(Decimal("0.01"))
            carbs = (recipe.carbohydrate_g * factor).quantize(Decimal("0.01"))
            desc = desc or recipe.name
        else:
            # manual — user-declared values, server validates ranges only
            if cal is None or protein is None or fat is None or carbs is None:
                raise NutritionLogValidationError(
                    "Для manual нужны calories и макросы.",
                )
            if not desc:
                raise NutritionLogValidationError("description обязателен для manual.")
            self._validate_ranges(cal, protein, fat, carbs)

        assert cal is not None and protein is not None and fat is not None and carbs is not None
        self._validate_ranges(cal, protein, fat, carbs)
        row = NutritionLog(
            user_id=user_id,
            logged_on=logged_on,
            meal_type=meal_type,
            recipe_id=recipe_id,
            meal_plan_item_id=meal_plan_item_id,
            description=desc[:255],
            calories_kcal=cal,
            protein_g=Decimal(str(protein)),
            fat_g=Decimal(str(fat)),
            carbohydrate_g=Decimal(str(carbs)),
            servings=Decimal(str(servings)),
            source=source,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def update(
        self,
        user_id: UUID,
        log_id: UUID,
        *,
        description: str | None = None,
        calories_kcal: int | None = None,
        protein_g: Decimal | None = None,
        fat_g: Decimal | None = None,
        carbohydrate_g: Decimal | None = None,
        servings: Decimal | None = None,
        meal_type: str | None = None,
    ) -> NutritionLog:
        row = await self._session.get(NutritionLog, log_id)
        if row is None or row.user_id != user_id:
            raise NutritionLogNotFound()
        if row.source != "manual":
            raise NutritionLogValidationError(
                "Редактировать можно только manual-записи."
            )
        if description is not None:
            row.description = description.strip()[:255]
        if meal_type is not None:
            if meal_type not in {"breakfast", "lunch", "dinner", "snack"}:
                raise NutritionLogValidationError("Некорректный meal_type.")
            row.meal_type = meal_type
        if calories_kcal is not None:
            row.calories_kcal = calories_kcal
        if protein_g is not None:
            row.protein_g = protein_g
        if fat_g is not None:
            row.fat_g = fat_g
        if carbohydrate_g is not None:
            row.carbohydrate_g = carbohydrate_g
        if servings is not None:
            row.servings = servings
        self._validate_ranges(
            row.calories_kcal, row.protein_g, row.fat_g, row.carbohydrate_g
        )
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def delete(self, user_id: UUID, log_id: UUID) -> None:
        row = await self._session.get(NutritionLog, log_id)
        if row is None or row.user_id != user_id:
            raise NutritionLogNotFound()
        await self._session.delete(row)
        await self._session.commit()

    async def day_totals(self, user_id: UUID, on_date: date) -> dict[str, Decimal | int]:
        logs = await self.list_logs(user_id, logged_on=on_date)
        return {
            "calories_kcal": sum(r.calories_kcal for r in logs),
            "protein_g": sum((r.protein_g for r in logs), Decimal("0")),
            "fat_g": sum((r.fat_g for r in logs), Decimal("0")),
            "carbohydrate_g": sum((r.carbohydrate_g for r in logs), Decimal("0")),
            "entries": len(logs),
        }

    async def get_by_meal_plan_item(
        self, user_id: UUID, meal_plan_item_id: UUID
    ) -> NutritionLog | None:
        statement = select(NutritionLog).where(
            NutritionLog.user_id == user_id,
            NutritionLog.meal_plan_item_id == meal_plan_item_id,
            NutritionLog.source == "meal_plan_item",
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def upsert_from_meal_plan_item(
        self, user_id: UUID, item: MealPlanItem, *, commit: bool = True
    ) -> NutritionLog:
        """Create or update the nutrition_log tied to a completed meal_plan_item."""
        recipe = await self._session.get(Recipe, item.recipe_id)
        description = (recipe.name if recipe else item.meal_type)[:255]
        existing = await self.get_by_meal_plan_item(user_id, item.id)
        if existing is not None:
            existing.logged_on = item.planned_date
            existing.meal_type = item.meal_type
            existing.recipe_id = item.recipe_id
            existing.description = description
            existing.calories_kcal = item.calories_kcal
            existing.protein_g = item.protein_g
            existing.fat_g = item.fat_g
            existing.carbohydrate_g = item.carbohydrate_g
            existing.servings = item.servings
            existing.source = "meal_plan_item"
            if commit:
                await self._session.commit()
                await self._session.refresh(existing)
            else:
                await self._session.flush()
            return existing

        row = NutritionLog(
            user_id=user_id,
            logged_on=item.planned_date,
            meal_type=item.meal_type,
            recipe_id=item.recipe_id,
            meal_plan_item_id=item.id,
            description=description,
            calories_kcal=item.calories_kcal,
            protein_g=item.protein_g,
            fat_g=item.fat_g,
            carbohydrate_g=item.carbohydrate_g,
            servings=item.servings,
            source="meal_plan_item",
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
            await self._session.refresh(row)
        else:
            await self._session.flush()
        return row

    async def delete_by_meal_plan_item(
        self, user_id: UUID, meal_plan_item_id: UUID, *, commit: bool = True
    ) -> bool:
        row = await self.get_by_meal_plan_item(user_id, meal_plan_item_id)
        if row is None:
            return False
        await self._session.delete(row)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return True

    @staticmethod
    def _validate_ranges(
        calories: int,
        protein: Decimal,
        fat: Decimal,
        carbs: Decimal,
    ) -> None:
        if calories < 0 or calories > 10000:
            raise NutritionLogValidationError("calories_kcal вне диапазона.")
        for name, value in (
            ("protein_g", protein),
            ("fat_g", fat),
            ("carbohydrate_g", carbs),
        ):
            if Decimal(str(value)) < 0 or Decimal(str(value)) > 1000:
                raise NutritionLogValidationError(f"{name} вне диапазона.")
