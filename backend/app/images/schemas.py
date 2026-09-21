"""Image domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RecipeImageOut(BaseModel):
    id: UUID
    recipe_id: UUID
    status: str
    url: str | None = None
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    retry_allowed: bool = False
    updated_at: datetime


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    model: str
    size: str | None = None
    quality: str | None = None
    output_format: str = "webp"


@dataclass(frozen=True)
class ImageGenerationResult:
    content: bytes
    model: str
    duration_ms: int = 0
    revised_prompt: str | None = None
