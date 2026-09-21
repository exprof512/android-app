"""Convert validated AI recipe candidates into RecipeEngine drafts."""

from __future__ import annotations

from decimal import Decimal

from app.ai.schemas import RecipeCandidate
from app.recipes.engine import IngredientDraft, RecipeDraft


def recipe_candidate_to_draft(
    candidate: RecipeCandidate, *, ai_model: str | None = None
) -> RecipeDraft:
    return RecipeDraft(
        name=candidate.name,
        description=candidate.description,
        servings=candidate.servings,
        cooking_method=candidate.cooking_method,
        cook_time_minutes=candidate.cook_time_minutes,
        ingredients=[
            IngredientDraft(
                name=item.name,
                quantity=Decimal(str(item.quantity)),
                unit=item.unit,
            )
            for item in candidate.ingredients
        ],
        steps=list(candidate.steps),
        ai_model=ai_model,
    )
