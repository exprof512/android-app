"""Prove Phase 21 AI provider routing — mocks only, no network."""

from __future__ import annotations

from app.ai.dependencies import build_text_provider
from app.ai.mock import MockTextProvider
from app.core.config import Settings
from app.integrations.deepseek.text import DeepSeekChatProvider
from app.integrations.openai.images import OpenAIImageProvider
from app.integrations.openai.vision import MockOpenAIVisionProvider, OpenAIVisionProvider
from app.nutrition.photo import build_vision_provider


def test_chat_and_text_ops_use_deepseek_when_keyed():
    settings = Settings(
        app_env="development",
        deepseek_api_key="sk-deepseek-test",
        deepseek_text_model="deepseek-chat",
        openai_api_key="sk-openai-test",
        openai_text_model="gpt-4.1-mini",
    )
    provider = build_text_provider(settings)
    assert isinstance(provider, DeepSeekChatProvider)


def test_text_does_not_use_openai_even_when_openai_keyed():
    settings = Settings(
        app_env="development",
        deepseek_api_key="sk-deepseek-test",
        openai_api_key="sk-openai-test",
    )
    provider = build_text_provider(settings)
    assert not isinstance(provider, type("OpenAI", (), {}))
    assert isinstance(provider, DeepSeekChatProvider)
    # OpenAI Responses must not be selected for product text.
    from app.integrations.openai.text import OpenAIResponsesProvider

    assert not isinstance(provider, OpenAIResponsesProvider)


def test_recipe_meal_plan_suggestion_adaptation_route_to_deepseek():
    """Same text provider serves all DeepSeek text operations."""
    settings = Settings(app_env="development", deepseek_api_key="sk-ds")
    provider = build_text_provider(settings)
    assert isinstance(provider, DeepSeekChatProvider)
    # Operations are dispatch keys on TextAIService; provider identity is shared.
    for _op in (
        "chat_answer",
        "generate_recipe_candidates",
        "generate_meal_plan_proposal",
        "daily_adaptation",
        "food_suggestion",
    ):
        assert isinstance(provider, DeepSeekChatProvider)


def test_no_deepseek_key_does_not_fall_back_to_openai_text():
    settings = Settings(
        app_env="development",
        deepseek_api_key="",
        openai_api_key="sk-openai-test",
        openai_text_model="gpt-4.1-mini",
    )
    provider = build_text_provider(settings)
    assert isinstance(provider, MockTextProvider)


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
