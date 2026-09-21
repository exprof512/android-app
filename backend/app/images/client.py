"""Typed image provider boundary."""

from __future__ import annotations

from typing import Protocol

from app.images.schemas import ImageGenerationRequest, ImageGenerationResult


class ImageGenerationProvider(Protocol):
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...
