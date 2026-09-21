"""Object-key helpers for recipe images."""

from __future__ import annotations

from uuid import UUID


def original_key(recipe_id: UUID, image_id: UUID, fmt: str) -> str:
    return f"images/recipes/{recipe_id}/{image_id}/original.{fmt}"


def thumbnail_key(recipe_id: UUID, image_id: UUID, fmt: str) -> str:
    return f"images/recipes/{recipe_id}/{image_id}/thumbnail.{fmt}"
