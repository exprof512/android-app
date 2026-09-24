"""AI operation registry: logical ops → TextAI keys and quota features."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.versions import (
    ADAPT_PROMPT_VERSION,
    CHAT_PROMPT_VERSION,
    PLAN_PROMPT_VERSION,
    RECIPE_PROMPT_VERSION,
    REPLACEMENT_PROMPT_VERSION,
    SUBSTITUTION_PROMPT_VERSION,
    SUGGESTION_PROMPT_VERSION,
    VARIANT_PROMPT_VERSION,
)
from app.entitlements import constants as entitlement_constants

# TextAIService / OPERATION_SCHEMAS keys
OP_GENERATE_RECIPE_CANDIDATES = "generate_recipe_candidates"
OP_GENERATE_MEAL_PLAN_PROPOSAL = "generate_meal_plan_proposal"
OP_REPLACE_MEAL_ITEM = "replace_meal_item"
OP_CHAT_ANSWER = "chat_answer"
OP_FOOD_SUGGESTION = "food_suggestion"
OP_DAILY_ADAPTATION = "daily_adaptation"
OP_INGREDIENT_SUBSTITUTION = "ingredient_substitution"
OP_RECIPE_VARIANT = "recipe_variant"


@dataclass(frozen=True)
class AIOperation:
    """Logical product operation with quota and prompt metadata."""

    key: str
    text_operation: str | None
    quota_feature: str | None
    prompt_version: str | None


# Product-facing operation names (Phase 20 audit).
plan_generation = AIOperation(
    key="plan_generation",
    text_operation=OP_GENERATE_MEAL_PLAN_PROPOSAL,
    quota_feature=entitlement_constants.FEATURE_MEAL_PLAN_GENERATE,
    prompt_version=PLAN_PROMPT_VERSION,
)
meal_replacement = AIOperation(
    key="meal_replacement",
    text_operation=OP_REPLACE_MEAL_ITEM,
    quota_feature=entitlement_constants.FEATURE_MEAL_REPLACE,
    prompt_version=REPLACEMENT_PROMPT_VERSION,
)
recipe_generation = AIOperation(
    key="recipe_generation",
    text_operation=OP_GENERATE_RECIPE_CANDIDATES,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=RECIPE_PROMPT_VERSION,
)
recipe_variant = AIOperation(
    key="recipe_variant",
    text_operation=OP_RECIPE_VARIANT,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=VARIANT_PROMPT_VERSION,
)
ingredient_substitution = AIOperation(
    key="ingredient_substitution",
    text_operation=OP_INGREDIENT_SUBSTITUTION,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=SUBSTITUTION_PROMPT_VERSION,
)
daily_adaptation = AIOperation(
    key="daily_adaptation",
    text_operation=OP_DAILY_ADAPTATION,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=ADAPT_PROMPT_VERSION,
)
food_suggestion = AIOperation(
    key="food_suggestion",
    text_operation=OP_FOOD_SUGGESTION,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=SUGGESTION_PROMPT_VERSION,
)
shopping_optimization = AIOperation(
    key="shopping_optimization",
    text_operation=None,
    quota_feature=entitlement_constants.FEATURE_AI_RECOMMENDATION,
    prompt_version=None,
)
chat = AIOperation(
    key="chat",
    text_operation=OP_CHAT_ANSWER,
    quota_feature=entitlement_constants.FEATURE_CHAT_MESSAGE,
    prompt_version=CHAT_PROMPT_VERSION,
)

OPERATIONS: dict[str, AIOperation] = {
    op.key: op
    for op in (
        plan_generation,
        meal_replacement,
        recipe_generation,
        recipe_variant,
        ingredient_substitution,
        daily_adaptation,
        food_suggestion,
        shopping_optimization,
        chat,
    )
}

PROMPT_VERSION_BY_TEXT_OP: dict[str, str] = {
    OP_GENERATE_RECIPE_CANDIDATES: RECIPE_PROMPT_VERSION,
    OP_GENERATE_MEAL_PLAN_PROPOSAL: PLAN_PROMPT_VERSION,
    OP_REPLACE_MEAL_ITEM: REPLACEMENT_PROMPT_VERSION,
    OP_CHAT_ANSWER: CHAT_PROMPT_VERSION,
    OP_FOOD_SUGGESTION: SUGGESTION_PROMPT_VERSION,
    OP_DAILY_ADAPTATION: ADAPT_PROMPT_VERSION,
    OP_INGREDIENT_SUBSTITUTION: SUBSTITUTION_PROMPT_VERSION,
    OP_RECIPE_VARIANT: VARIANT_PROMPT_VERSION,
}
