"""Mock image provider for tests — never calls OpenAI."""

from __future__ import annotations

import io
import time

from PIL import Image

from app.images.errors import ImageProviderError
from app.images.schemas import ImageGenerationRequest, ImageGenerationResult


def _tiny_png() -> bytes:
    image = Image.new("RGB", (64, 64), color=(200, 120, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class MockImageProvider:
    def __init__(
        self,
        *,
        content: bytes | None = None,
        fail_times: int = 0,
        model: str = "mock-image-model",
    ) -> None:
        self._content = content if content is not None else _tiny_png()
        self._fail_times = fail_times
        self._model = model
        self.calls: list[ImageGenerationRequest] = []

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        self.calls.append(request)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise ImageProviderError(
                code="ai_provider_timeout",
                message="mock timeout",
                retryable=True,
            )
        return ImageGenerationResult(
            content=self._content,
            model=self._model,
            duration_ms=5,
        )
