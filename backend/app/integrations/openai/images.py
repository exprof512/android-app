"""Image Generation provider stub — full pipeline arrives in Phase 7."""

from __future__ import annotations

from typing import Protocol


class ImageGenerationProvider(Protocol):
    """Production and mock image providers implement this contract later."""

    async def generate(self, *, prompt: str, model: str) -> bytes: ...
