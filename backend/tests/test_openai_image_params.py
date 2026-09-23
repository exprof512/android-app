"""Unit tests for GPT Image request param resolution."""

from __future__ import annotations

from app.integrations.openai.image_params import (
    build_images_generate_params,
    resolve_image_settings,
)


def test_gpt_image_1_defaults_and_omits_dalle_knobs() -> None:
    resolved = resolve_image_settings(
        model="gpt-image-1",
        size="",
        quality="",
        storage_format="webp",
        provider_format="",
    )
    assert resolved.model == "gpt-image-1"
    assert resolved.size == "1024x1024"
    assert resolved.quality == "low"
    assert resolved.provider_format == "png"
    assert resolved.storage_format == "webp"

    params = build_images_generate_params(prompt="plated chicken", settings=resolved)
    assert params == {
        "model": "gpt-image-1",
        "prompt": "plated chicken",
        "size": "1024x1024",
        "quality": "low",
        "output_format": "png",
    }
    assert "response_format" not in params
    assert "style" not in params
    assert "n" not in params


def test_maps_dalle_quality_and_invalid_size() -> None:
    resolved = resolve_image_settings(
        model="gpt-image-1",
        size="512x512",
        quality="hd",
        storage_format="webp",
    )
    assert resolved.size == "1024x1024"
    assert resolved.quality == "high"


def test_storage_format_independent_of_provider() -> None:
    resolved = resolve_image_settings(
        model="gpt-image-1",
        size="1024x1024",
        quality="medium",
        storage_format="webp",
        provider_format="png",
    )
    assert resolved.provider_format == "png"
    assert resolved.storage_format == "webp"
