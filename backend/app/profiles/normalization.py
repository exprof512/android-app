"""Food name normalization shared by preferences, restrictions and pantry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedName:
    normalized: str
    display: str


def normalize_food_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_unique(values: list[str]) -> list[NormalizedName]:
    """Drop blanks and duplicates while keeping the first spelling the user typed."""
    seen: dict[str, NormalizedName] = {}
    for value in values:
        normalized = normalize_food_name(value)
        if not normalized or normalized in seen:
            continue
        seen[normalized] = NormalizedName(normalized=normalized, display=value.strip())
    return list(seen.values())
