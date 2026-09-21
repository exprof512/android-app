"""Shared response field types."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Money and weights stay Decimal in Python and numeric in PostgreSQL; the JSON
# contract uses plain numbers.
DecimalOut = Annotated[
    Decimal, PlainSerializer(float, return_type=float, when_used="json")
]
