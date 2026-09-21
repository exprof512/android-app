"""Canonical keys for ingredient and recipe names."""

from __future__ import annotations

import re

_PUNCTUATION = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


def canonical_key(value: str) -> str:
    """Lowercase, drop punctuation, unify ``ё`` and collapse whitespace.

    AI ingredient names are not canonical until they match this key in the catalog.
    """
    lowered = value.strip().lower().replace("ё", "е")
    without_punctuation = _PUNCTUATION.sub(" ", lowered)
    return _WHITESPACE.sub(" ", without_punctuation).strip()
