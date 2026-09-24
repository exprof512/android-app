"""Entitlement feature keys and default free-tier windows."""

from __future__ import annotations

FEATURE_MEAL_PLAN_GENERATE = "meal_plan_generate"
FEATURE_MEAL_REPLACE = "meal_plan_replace"
FEATURE_CHAT_MESSAGE = "chat_message"
FEATURE_IMAGE_REGENERATE = "image_regenerate"
FEATURE_AI_RECOMMENDATION = "ai_recommendation"

PREMIUM_ONLY_FEATURES = frozenset({FEATURE_IMAGE_REGENERATE})

TIER_FREE = "free"
TIER_PREMIUM = "premium"
STATUS_ACTIVE = "active"
