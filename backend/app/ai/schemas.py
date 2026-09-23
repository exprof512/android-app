"""Structured Outputs schemas for Text AI operations.

AI may propose structure; NutritionEngine / RecipeEngine own final math.

OpenAI Responses API with ``strict: true`` requires every property key to appear
in ``required`` (optional fields use ``anyOf: [T, null]`` and stay required).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.recipes import constants

CookingMethod = Literal[
    "boil", "fry", "bake", "stew", "grill", "steam", "raw", "mixed"
]
MealType = Literal["breakfast", "lunch", "dinner", "snack"]
RecipeUnit = Literal["g", "kg", "ml", "l", "tbsp", "tsp", "piece"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecipeIngredientCandidate(StrictModel):
    name: str = Field(min_length=1, max_length=constants.NAME_MAX_LENGTH)
    quantity: float = Field(gt=0, le=float(constants.QUANTITY_MAX))
    unit: RecipeUnit


class RecipeCandidate(StrictModel):
    name: str = Field(min_length=1, max_length=constants.NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=constants.DESCRIPTION_MAX_LENGTH)
    servings: int = Field(
        ge=constants.SERVINGS_MIN, le=constants.SERVINGS_MAX
    )
    cooking_method: CookingMethod
    cook_time_minutes: int = Field(
        ge=constants.COOK_TIME_MINUTES_MIN, le=constants.COOK_TIME_MINUTES_MAX
    )
    ingredients: list[RecipeIngredientCandidate] = Field(
        min_length=constants.INGREDIENTS_MIN, max_length=constants.INGREDIENTS_MAX
    )
    steps: list[str] = Field(
        min_length=constants.STEPS_MIN, max_length=constants.STEPS_MAX
    )
    rationale: str | None = Field(default=None, max_length=1000)

    @field_validator("steps")
    @classmethod
    def steps_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [step.strip() for step in value if step and step.strip()]
        if len(cleaned) < constants.STEPS_MIN:
            raise ValueError("steps_required")
        for step in cleaned:
            if len(step) > constants.STEP_MAX_LENGTH:
                raise ValueError("step_too_long")
        return cleaned


class RecipeCandidatesResponse(StrictModel):
    recipes: list[RecipeCandidate] = Field(min_length=1, max_length=8)


class MealPlanSlotProposal(StrictModel):
    planned_date: str = Field(min_length=10, max_length=10)
    meal_type: MealType
    recipe_index: int = Field(ge=0)
    servings: float = Field(gt=0, le=12)


class MealPlanProposalResponse(StrictModel):
    recipes: list[RecipeCandidate] = Field(min_length=1, max_length=40)
    slots: list[MealPlanSlotProposal] = Field(min_length=1, max_length=56)
    rationale: str | None = Field(default=None, max_length=2000)


class ReplaceMealResponse(StrictModel):
    recipes: list[RecipeCandidate] = Field(min_length=1, max_length=5)
    reason: str = Field(min_length=1, max_length=1000)


class ChatSuggestedAction(StrictModel):
    type: Literal["replace_meal_item", "open_shopping_list", "explain_balance", "none"]
    label: str = Field(min_length=1, max_length=120)
    # Free-form dict is rejected by OpenAI strict schemas; keep optional JSON string.
    payload: str | None = Field(default=None, max_length=2000)


class ChatAnswerResponse(StrictModel):
    answer: str = Field(min_length=1, max_length=4000)
    suggested_actions: list[ChatSuggestedAction] = Field(default_factory=list, max_length=5)
    warnings: list[str] = Field(default_factory=list, max_length=5)


OPERATION_SCHEMAS: dict[str, type[BaseModel]] = {
    "generate_recipe_candidates": RecipeCandidatesResponse,
    "generate_meal_plan_proposal": MealPlanProposalResponse,
    "replace_meal_item": ReplaceMealResponse,
    "chat_answer": ChatAnswerResponse,
}


def json_schema_for(operation: str) -> dict[str, Any]:
    model = OPERATION_SCHEMAS[operation]
    schema = model.model_json_schema()
    return make_openai_strict_schema(schema)


def make_openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten $defs and satisfy OpenAI strict Structured Outputs rules."""
    inlined = _inline_defs(schema)
    return _enforce_strict(inlined)


def _inline_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten $defs/$ref for providers that prefer a single object schema."""
    defs = schema.pop("$defs", None) or schema.pop("definitions", None) or {}

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"].rsplit("/", 1)[-1]
                return resolve(defs[ref])
            return {key: resolve(value) for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(schema)


def _enforce_strict(node: Any) -> Any:
    """Recursively: required=all properties; drop defaults; forbid extras."""
    if isinstance(node, list):
        return [_enforce_strict(item) for item in node]
    if not isinstance(node, dict):
        return node

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "default":
            # Defaults are incompatible with OpenAI strict required-all-keys.
            continue
        out[key] = _enforce_strict(value)

    if out.get("type") == "object" or "properties" in out:
        props = out.get("properties")
        if isinstance(props, dict):
            out["additionalProperties"] = False
            out["required"] = list(props.keys())
            out["properties"] = {
                name: _enforce_strict(prop) for name, prop in props.items()
            }
    return out
