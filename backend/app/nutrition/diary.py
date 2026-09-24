"""Nutrition diary service — backend-authoritative macros."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError, OwnershipDenied
from app.meal_plans.models import MealPlanItem
from app.nutrition.food_match import nutrition_for_grams
from app.nutrition.models import LOG_SOURCES, MEAL_TYPES, NutritionLog
from app.recipes.models import Ingredient, Recipe


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


_EDITABLE_SOURCES = frozenset({"manual", "photo_ai", "search", "quick_add"})


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
        ingredient_id: UUID | None = None,
        calories_kcal: int | None = None,
        protein_g: Decimal | None = None,
        fat_g: Decimal | None = None,
        carbohydrate_g: Decimal | None = None,
        servings: Decimal = Decimal("1"),
        quantity_g: Decimal | None = None,
        unit: str | None = None,
        notes: str | None = None,
        confidence: Decimal | None = None,
    ) -> NutritionLog:
        if meal_type not in MEAL_TYPES:
            raise NutritionLogValidationError("Некорректный meal_type.")
        if source not in LOG_SOURCES:
            raise NutritionLogValidationError("Некорректный source.")

        desc = (description or "").strip()
        cal = calories_kcal
        protein = protein_g
        fat = fat_g
        carbs = carbohydrate_g
        qty = quantity_g

        if source in {"meal_plan_item", "planned_meal"}:
            if meal_plan_item_id is None:
                raise NutritionLogValidationError("meal_plan_item_id обязателен.")
            item = await self._session.get(MealPlanItem, meal_plan_item_id)
            if item is None:
                raise NutritionLogValidationError("Приём пищи не найден.")
            from app.meal_plans.models import MealPlan

            plan_row = await self._session.get(MealPlan, item.meal_plan_id)
            if plan_row is None or plan_row.user_id != user_id:
                raise OwnershipDenied()
            existing = await self.get_by_meal_plan_item(user_id, meal_plan_item_id)
            if existing is not None:
                return existing
            cal = item.calories_kcal
            protein = item.protein_g
            fat = item.fat_g
            carbs = item.carbohydrate_g
            servings = item.servings
            recipe_id = item.recipe_id
            recipe = await self._session.get(Recipe, item.recipe_id)
            desc = desc or (recipe.name if recipe else item.meal_type)
            source = "meal_plan_item"
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
        elif source in {"search", "photo_ai"} and ingredient_id is not None:
            ingredient = await self._session.get(Ingredient, ingredient_id)
            if ingredient is None or not ingredient.is_active:
                raise NutritionLogValidationError("Ингредиент не найден.")
            if qty is None or qty <= 0:
                raise NutritionLogValidationError("quantity_g обязателен.")
            macros = nutrition_for_grams(ingredient, Decimal(str(qty)))
            cal = int(macros["calories_kcal"])
            protein = macros["protein_g"]  # type: ignore[assignment]
            fat = macros["fat_g"]  # type: ignore[assignment]
            carbs = macros["carbohydrate_g"]  # type: ignore[assignment]
            desc = desc or ingredient.canonical_name
            unit = unit or "g"
        elif source == "quick_add":
            if cal is None:
                raise NutritionLogValidationError("Для quick_add нужны calories_kcal.")
            protein = protein if protein is not None else Decimal("0")
            fat = fat if fat is not None else Decimal("0")
            carbs = carbs if carbs is not None else Decimal("0")
            desc = desc or "Быстрый ввод"
        else:
            # manual — user-declared values
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
            ingredient_id=ingredient_id,
            description=desc[:255],
            calories_kcal=cal,
            protein_g=Decimal(str(protein)),
            fat_g=Decimal(str(fat)),
            carbohydrate_g=Decimal(str(carbs)),
            servings=Decimal(str(servings)),
            quantity_g=Decimal(str(qty)) if qty is not None else None,
            unit=unit,
            notes=(notes[:500] if notes else None),
            confidence=confidence,
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
        quantity_g: Decimal | None = None,
        ingredient_id: UUID | None = None,
        notes: str | None = None,
    ) -> NutritionLog:
        row = await self._session.get(NutritionLog, log_id)
        if row is None or row.user_id != user_id:
            raise NutritionLogNotFound()
        if row.source not in _EDITABLE_SOURCES:
            raise NutritionLogValidationError(
                "Редактировать можно только записи manual/photo_ai/search/quick_add."
            )
        if description is not None:
            row.description = description.strip()[:255]
        if meal_type is not None:
            if meal_type not in MEAL_TYPES:
                raise NutritionLogValidationError("Некорректный meal_type.")
            row.meal_type = meal_type
        if notes is not None:
            row.notes = notes[:500] if notes else None

        # Recalculate from ingredient + grams when provided.
        if ingredient_id is not None or quantity_g is not None:
            ing_id = ingredient_id or row.ingredient_id
            qty = quantity_g if quantity_g is not None else row.quantity_g
            if ing_id is not None and qty is not None and qty > 0:
                ingredient = await self._session.get(Ingredient, ing_id)
                if ingredient is None:
                    raise NutritionLogValidationError("Ингредиент не найден.")
                macros = nutrition_for_grams(ingredient, Decimal(str(qty)))
                row.ingredient_id = ing_id
                row.quantity_g = Decimal(str(qty))
                row.unit = "g"
                row.calories_kcal = int(macros["calories_kcal"])
                row.protein_g = macros["protein_g"]  # type: ignore[assignment]
                row.fat_g = macros["fat_g"]  # type: ignore[assignment]
                row.carbohydrate_g = macros["carbohydrate_g"]  # type: ignore[assignment]
                if not row.description:
                    row.description = ingredient.canonical_name
            elif quantity_g is not None:
                row.quantity_g = quantity_g

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
        # Deleting a plan-linked log must uncomplete the slot so Today matches Diary.
        item_id = row.meal_plan_item_id
        await self._session.delete(row)
        if item_id is not None:
            item = await self._session.get(MealPlanItem, item_id)
            if item is not None and (item.is_completed or item.status == "completed"):
                item.is_completed = False
                item.completed_at = None
                item.status = "planned"
        await self._session.commit()

    async def duplicate(self, user_id: UUID, log_id: UUID) -> NutritionLog:
        row = await self._session.get(NutritionLog, log_id)
        if row is None or row.user_id != user_id:
            raise NutritionLogNotFound()
        if row.source == "meal_plan_item" or row.meal_plan_item_id is not None:
            raise NutritionLogValidationError(
                "Нельзя дублировать запись из плана — это удваивает калории. "
                "Добавьте еду вручную, если съели ещё раз.",
            )
        copy = NutritionLog(
            user_id=user_id,
            logged_on=row.logged_on,
            meal_type=row.meal_type,
            recipe_id=row.recipe_id,
            meal_plan_item_id=None,
            ingredient_id=row.ingredient_id,
            description=row.description,
            calories_kcal=row.calories_kcal,
            protein_g=row.protein_g,
            fat_g=row.fat_g,
            carbohydrate_g=row.carbohydrate_g,
            servings=row.servings,
            quantity_g=row.quantity_g,
            unit=row.unit,
            notes=row.notes,
            confidence=None,
            source=row.source if row.source in _EDITABLE_SOURCES else "manual",
        )
        self._session.add(copy)
        await self._session.commit()
        await self._session.refresh(copy)
        return copy

    async def day_totals(self, user_id: UUID, on_date: date) -> dict[str, Decimal | int]:
        logs = await self.list_logs(user_id, logged_on=on_date)
        return {
            "calories_kcal": sum(r.calories_kcal for r in logs),
            "protein_g": sum((r.protein_g for r in logs), Decimal("0")),
            "fat_g": sum((r.fat_g for r in logs), Decimal("0")),
            "carbohydrate_g": sum((r.carbohydrate_g for r in logs), Decimal("0")),
            "entries": len(logs),
        }

    async def day_summary(self, user_id: UUID, on_date: date) -> dict:
        logs = await self.list_logs(user_id, logged_on=on_date)
        by_meal: dict[str, list[NutritionLog]] = {m: [] for m in MEAL_TYPES}
        for row in logs:
            by_meal.setdefault(row.meal_type, []).append(row)
        totals = await self.day_totals(user_id, on_date)
        return {
            "date": on_date,
            "totals": totals,
            "meals": {
                meal: [
                    {
                        "id": str(r.id),
                        "description": r.description,
                        "calories_kcal": r.calories_kcal,
                        "protein_g": float(r.protein_g),
                        "fat_g": float(r.fat_g),
                        "carbohydrate_g": float(r.carbohydrate_g),
                        "quantity_g": float(r.quantity_g) if r.quantity_g else None,
                        "source": r.source,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in items
                ]
                for meal, items in by_meal.items()
                if items
            },
        }

    async def history(
        self, user_id: UUID, *, days: int = 7, end: date | None = None
    ) -> list[dict]:
        end_date = end or date.today()
        start = end_date - timedelta(days=max(1, min(days, 31)) - 1)
        statement = (
            select(NutritionLog)
            .where(
                NutritionLog.user_id == user_id,
                NutritionLog.logged_on >= start,
                NutritionLog.logged_on <= end_date,
            )
            .order_by(NutritionLog.logged_on.desc())
        )
        rows = list((await self._session.execute(statement)).scalars())
        by_day: dict[date, list[NutritionLog]] = {}
        for row in rows:
            by_day.setdefault(row.logged_on, []).append(row)
        out: list[dict] = []
        cursor = end_date
        while cursor >= start:
            day_rows = by_day.get(cursor, [])
            out.append(
                {
                    "date": cursor,
                    "calories_kcal": sum(r.calories_kcal for r in day_rows),
                    "protein_g": float(
                        sum((r.protein_g for r in day_rows), Decimal("0"))
                    ),
                    "fat_g": float(sum((r.fat_g for r in day_rows), Decimal("0"))),
                    "carbohydrate_g": float(
                        sum((r.carbohydrate_g for r in day_rows), Decimal("0"))
                    ),
                    "entries": len(day_rows),
                }
            )
            cursor -= timedelta(days=1)
        return out

    async def recent_foods(self, user_id: UUID, *, limit: int = 12) -> list[dict]:
        statement = (
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id)
            .order_by(NutritionLog.created_at.desc())
            .limit(80)
        )
        rows = list((await self._session.execute(statement)).scalars())
        seen: set[str] = set()
        out: list[dict] = []
        for row in rows:
            key = (row.ingredient_id and str(row.ingredient_id)) or row.description.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "description": row.description,
                    "ingredient_id": str(row.ingredient_id) if row.ingredient_id else None,
                    "quantity_g": float(row.quantity_g) if row.quantity_g else None,
                    "calories_kcal": row.calories_kcal,
                    "protein_g": float(row.protein_g),
                    "fat_g": float(row.fat_g),
                    "carbohydrate_g": float(row.carbohydrate_g),
                    "source": row.source,
                }
            )
            if len(out) >= limit:
                break
        return out

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
