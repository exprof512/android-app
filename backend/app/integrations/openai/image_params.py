"""Model-aware OpenAI Images API request building.

Separates provider wire format from FoodAI storage format.
GPT Image models reject DALL·E-only knobs (`response_format`, `style`, …)
with HTTP 400 — this module never sends them.
"""

from __future__ import annotations

from dataclasses import dataclass

GPT_IMAGE_1_SIZES = frozenset({"1024x1024", "1024x1536", "1536x1024", "auto"})
GPT_IMAGE_1_QUALITIES = frozenset({"low", "medium", "high", "auto"})
GPT_IMAGE_2_QUALITIES = frozenset(
    {"low", "medium", "high", "auto", "xhigh", "max"}
)
GPT_IMAGE_PROVIDER_FORMATS = frozenset({"png", "jpeg", "webp"})
STORAGE_FORMATS = frozenset({"webp", "jpeg"})

DEFAULT_MODEL = "gpt-image-1"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "low"
DEFAULT_PROVIDER_FORMAT = "png"
DEFAULT_STORAGE_FORMAT = "webp"


@dataclass(frozen=True)
class ResolvedImageSettings:
    model: str
    size: str
    quality: str
    provider_format: str
    storage_format: str


def normalize_model(raw: str | None) -> str:
    model = (raw or "").strip() or DEFAULT_MODEL
    aliases = {
        "gpt-image": "gpt-image-1",
        "gpt_image_1": "gpt-image-1",
        "gpt-image1": "gpt-image-1",
    }
    return aliases.get(model, model)


def resolve_image_settings(
    *,
    model: str | None,
    size: str | None,
    quality: str | None,
    storage_format: str | None,
    provider_format: str | None = None,
) -> ResolvedImageSettings:
    """Validate/normalize env knobs into a safe OpenAI + storage profile."""
    resolved_model = normalize_model(model)
    is_v2 = resolved_model.startswith("gpt-image-2")

    raw_size = (size or "").strip()
    raw_quality = (quality or "").strip().lower()
    raw_storage = (storage_format or "").strip().lower() or DEFAULT_STORAGE_FORMAT
    raw_provider = (provider_format or "").strip().lower() or DEFAULT_PROVIDER_FORMAT

    if raw_storage == "jpg":
        raw_storage = "jpeg"
    if raw_provider == "jpg":
        raw_provider = "jpeg"
    if raw_storage not in STORAGE_FORMATS:
        raw_storage = DEFAULT_STORAGE_FORMAT
    if raw_provider not in GPT_IMAGE_PROVIDER_FORMATS:
        raw_provider = DEFAULT_PROVIDER_FORMAT

    # Size: gpt-image-1 has a fixed set; gpt-image-2 is freer but we still
    # prefer a known square when unset/invalid for image-1.
    if not raw_size:
        resolved_size = DEFAULT_SIZE
    elif is_v2:
        resolved_size = raw_size
    elif raw_size in GPT_IMAGE_1_SIZES:
        resolved_size = raw_size
    else:
        resolved_size = DEFAULT_SIZE

    # Quality: map DALL·E names that 400 on GPT Image.
    if raw_quality in {"", "standard"}:
        resolved_quality = DEFAULT_QUALITY
    elif raw_quality == "hd":
        resolved_quality = "high"
    elif is_v2 and raw_quality in GPT_IMAGE_2_QUALITIES:
        resolved_quality = raw_quality
    elif raw_quality in GPT_IMAGE_1_QUALITIES:
        resolved_quality = raw_quality
    else:
        resolved_quality = DEFAULT_QUALITY

    return ResolvedImageSettings(
        model=resolved_model,
        size=resolved_size,
        quality=resolved_quality,
        provider_format=raw_provider,
        storage_format=raw_storage,
    )


def build_images_generate_params(
    *,
    prompt: str,
    settings: ResolvedImageSettings,
) -> dict[str, object]:
    """Return kwargs for ``client.images.generate`` — GPT Image safe subset only."""
    if not prompt.strip():
        raise ValueError("image_prompt_empty")

    return {
        "model": settings.model,
        "prompt": prompt,
        "size": settings.size,
        "quality": settings.quality,
        "output_format": settings.provider_format,
        # Never: response_format, style, n (API default n=1).
    }
