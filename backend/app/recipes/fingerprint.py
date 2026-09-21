"""Canonical recipe fingerprint used for reuse and deduplication."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.recipes.normalization import canonical_key


def recipe_fingerprint(
    *,
    name: str,
    cooking_method: str,
    servings: int,
    ingredients: Iterable[tuple[UUID, Decimal]],
) -> str:
    """SHA-256 over the canonicalized dish.

    Servings take part because the stored nutrition and cost are per serving, so
    the same grams split differently are different recipes.
    """
    parts = [
        canonical_key(name),
        cooking_method,
        str(servings),
    ]
    parts.extend(
        sorted(
            f"{ingredient_id}:{grams.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
            for ingredient_id, grams in ingredients
        )
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
