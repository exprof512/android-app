"""Staged validation of AI recipe candidates before persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence

from app.ai.drafts import recipe_candidate_to_draft
from app.ai.schemas import RecipeCandidate
from app.ai.unit_repair import repair_recipe_candidate_units
from app.nutrition.engine import NutritionEngine
from app.profiles.normalization import normalize_food_name
from app.recipes.engine import CanonicalRecipe, RecipeEngine
from app.recipes.errors import RecipeValidationError
from app.recipes.models import Ingredient


@dataclass
class ValidationResult:
    ok: bool
    error_codes: list[str] = field(default_factory=list)
    repaired_candidate: RecipeCandidate | None = None
    canonical: CanonicalRecipe | None = None
    warnings: list[str] = field(default_factory=list)


class AIResponseValidator:
    """Post-schema stages: ingredients, allergy, diversity, cook time, budget."""

    def __init__(self, nutrition: NutritionEngine) -> None:
        self._engine = RecipeEngine(nutrition)

    def validate_recipe_candidate(
        self,
        candidate: RecipeCandidate,
        *,
        catalog: dict[str, Ingredient],
        restricted_names: Sequence[str] = (),
        recent_recipe_ids: Sequence[str] = (),
        recent_recipe_names: Sequence[str] = (),
        max_cook_time_minutes: int | None = None,
        grocery_budget_weekly: float | None = None,
        meals_per_day: int | None = None,
    ) -> ValidationResult:
        error_codes: list[str] = []
        warnings: list[str] = []
        canonical: CanonicalRecipe | None = None

        working, repair_warnings = repair_recipe_candidate_units(candidate, catalog)
        warnings.extend(repair_warnings)
        repaired_candidate = working if working is not candidate else None

        # Stage: ingredients known + RecipeEngine canonicalize
        try:
            draft = recipe_candidate_to_draft(working)
            canonical = self._engine.canonicalize(draft, catalog)
            warnings.extend(canonical.warnings)
        except RecipeValidationError as exc:
            for detail in exc.details or []:
                reason = detail.get("reason", "")
                if reason == "unknown_ingredient":
                    error_codes.append("unknown_ingredient")
                else:
                    error_codes.append(f"recipe_{reason}" if reason else "recipe_invalid")
            if not error_codes:
                error_codes.append("recipe_invalid")

        # Stage: allergy / restriction
        restricted = {normalize_food_name(name) for name in restricted_names}
        restricted.discard("")
        if restricted:
            names = [ing.name for ing in working.ingredients]
            if canonical is not None:
                names.extend(ing.display_name for ing in canonical.ingredients)
            for name in names:
                key = normalize_food_name(name)
                if key and key in restricted:
                    error_codes.append("allergy_or_restriction")
                    break

        # Stage: diversity vs recent
        recent_names = {
            normalize_food_name(name) for name in recent_recipe_names if name
        }
        recent_names.discard("")
        cand_name = normalize_food_name(working.name)
        if cand_name and cand_name in recent_names:
            error_codes.append("duplicate_recent")

        # Stage: cook time
        cook = (
            canonical.cook_time_minutes
            if canonical is not None
            else working.cook_time_minutes
        )
        if max_cook_time_minutes is not None and cook > max_cook_time_minutes:
            error_codes.append("cook_time_exceeded")

        # Stage: budget soft check (weekly budget / meals_per_day * 7 ≈ per meal)
        if (
            grocery_budget_weekly is not None
            and grocery_budget_weekly > 0
            and canonical is not None
            and canonical.estimated_cost_amount is not None
        ):
            meals = max(1, meals_per_day or 3)
            soft_per_meal = Decimal(str(grocery_budget_weekly)) / Decimal(meals * 7)
            if canonical.estimated_cost_amount > soft_per_meal * Decimal("2.5"):
                warnings.append("budget_soft_exceeded")
                error_codes.append("budget_soft_exceeded")

        unique: list[str] = []
        seen: set[str] = set()
        for code in error_codes:
            if code not in seen:
                seen.add(code)
                unique.append(code)

        hard = [c for c in unique if c != "budget_soft_exceeded"]
        ok = not hard
        return ValidationResult(
            ok=ok,
            error_codes=unique,
            repaired_candidate=repaired_candidate if ok else None,
            canonical=canonical if ok else None,
            warnings=warnings,
        )

    def validate_from_context(
        self,
        candidate: RecipeCandidate,
        *,
        catalog: dict[str, Ingredient],
        context: dict[str, Any],
    ) -> ValidationResult:
        prefs = context.get("preferences") or {}
        disliked = prefs.get("disliked") if isinstance(prefs, dict) else []
        restrictions = list(context.get("restrictions") or [])
        if disliked:
            restrictions = list(restrictions) + list(disliked)
        return self.validate_recipe_candidate(
            candidate,
            catalog=catalog,
            restricted_names=restrictions,
            recent_recipe_ids=list(context.get("recent_recipe_ids") or []),
            recent_recipe_names=[
                r.get("name", "")
                for r in (context.get("recent_recipes") or [])
                if isinstance(r, dict)
            ],
            max_cook_time_minutes=context.get("max_cook_time_minutes"),
            grocery_budget_weekly=context.get("grocery_budget_weekly"),
            meals_per_day=context.get("meals_per_day"),
        )
