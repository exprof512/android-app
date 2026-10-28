"""Prove AI provider routing — mocks only, no network."""

from __future__ import annotations

from app.ai.dependencies import build_text_provider
from app.ai.fallback import FallbackTextProvider
from app.ai.mock import MockTextProvider
from app.core.config import Settings
from app.integrations.deepseek.text import DeepSeekChatProvider
from app.integrations.openai.images import OpenAIImageProvider
from app.integrations.openai.text import OpenAIResponsesProvider
from app.integrations.openai.vision import MockOpenAIVisionProvider, OpenAIVisionProvider
from app.nutrition.photo import build_vision_provider


def test_text_provider_prefers_deepseek_and_falls_back_to_openai():
    settings = Settings(
        app_env="development",
        deepseek_api_key="sk-deepseek-test",
        deepseek_text_model="deepseek-chat",
        openai_api_key="sk-openai-test",
        openai_text_model="gpt-4.1-mini",
    )
    provider = build_text_provider(settings)
    assert isinstance(provider, FallbackTextProvider)
    assert provider._providers[0][0] == "deepseek"
    assert provider._providers[1][0] == "openai"
    assert isinstance(provider._providers[1][1], OpenAIResponsesProvider)


def test_single_deepseek_key_uses_deepseek_directly():
    settings = Settings(
        app_env="development",
        deepseek_api_key="sk-deepseek-test",
        openai_api_key="",
    )
    assert isinstance(build_text_provider(settings), DeepSeekChatProvider)


def test_recipe_meal_plan_suggestion_adaptation_route_to_deepseek():
    """Same text provider serves all DeepSeek text operations."""
    settings = Settings(app_env="development", deepseek_api_key="sk-ds", openai_api_key="")
    provider = build_text_provider(settings)
    assert isinstance(provider, DeepSeekChatProvider)
    for _op in (
        "chat_answer",
        "generate_recipe_candidates",
        "generate_meal_plan_proposal",
        "daily_adaptation",
        "food_suggestion",
    ):
        assert isinstance(provider, DeepSeekChatProvider)


def test_openai_text_serves_when_deepseek_key_is_missing():
    settings = Settings(
        app_env="development",
        deepseek_api_key="",
        openai_api_key="sk-openai-test",
        openai_text_model="gpt-4.1-mini",
    )
    assert isinstance(build_text_provider(settings), OpenAIResponsesProvider)


def test_no_keys_keeps_the_mock_provider():
    settings = Settings(app_env="development", deepseek_api_key="", openai_api_key="")
    assert isinstance(build_text_provider(settings), MockTextProvider)


def test_food_photo_uses_openai_vision():
    settings = Settings(
        app_env="development",
        openai_api_key="sk-openai-test",
        openai_vision_model="gpt-4.1-mini",
        deepseek_api_key="sk-deepseek-test",
    )
    vision = build_vision_provider(settings)
    assert isinstance(vision, OpenAIVisionProvider)


def test_food_photo_mock_in_test_env():
    settings = Settings(app_env="test", openai_api_key="sk-openai-test")
    vision = build_vision_provider(settings)
    assert isinstance(vision, MockOpenAIVisionProvider)


def test_image_generation_uses_openai_image():
    provider = OpenAIImageProvider(api_key="sk-openai-test")
    assert isinstance(provider, OpenAIImageProvider)
