"""Decode, validate and optimize recipe images for mobile delivery."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

MAX_SOURCE_BYTES = 15 * 1024 * 1024
ORIGINAL_MAX_EDGE = 1280
THUMBNAIL_MAX_EDGE = 384
WEBP_QUALITY = 82


@dataclass(frozen=True)
class OptimizedImage:
    content: bytes
    width: int
    height: int
    format: str
    file_size: int


def optimize_pair(
    source: bytes, *, output_format: str = "webp"
) -> tuple[OptimizedImage, OptimizedImage]:
    if len(source) > MAX_SOURCE_BYTES:
        raise ValueError("image_too_large")
    if not source:
        raise ValueError("image_empty")

    with Image.open(io.BytesIO(source)) as image:
        image.load()
        rgb = image.convert("RGB")

    original = _encode(rgb, max_edge=ORIGINAL_MAX_EDGE, output_format=output_format)
    thumbnail = _encode(rgb, max_edge=THUMBNAIL_MAX_EDGE, output_format=output_format)
    return original, thumbnail


def _encode(image: Image.Image, *, max_edge: int, output_format: str) -> OptimizedImage:
    clone = image.copy()
    clone.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    fmt = output_format.lower()
    if fmt == "jpeg":
        clone.save(buffer, format="JPEG", quality=WEBP_QUALITY, optimize=True)
        mime_fmt = "jpeg"
    else:
        clone.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
        mime_fmt = "webp"
    data = buffer.getvalue()
    return OptimizedImage(
        content=data,
        width=clone.width,
        height=clone.height,
        format=mime_fmt,
        file_size=len(data),
    )
