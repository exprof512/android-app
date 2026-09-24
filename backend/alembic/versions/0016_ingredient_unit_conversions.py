"""Fill missing piece/density conversion factors for common AI units.

Revision ID: 0016_ingredient_unit_conversions
Revises: 0015_ai_recommendation_records
Create Date: 2026-09-24

"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision: str = "0016_ingredient_unit_conversions"
down_revision: str | Sequence[str] | None = "0015_ai_recommendation_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# canonical_name → (grams_per_piece | None, density_g_per_ml | None)
# Only fills NULL fields; does not overwrite curated values.
_CONVERSIONS: dict[str, tuple[Decimal | None, Decimal | None]] = {
    "Лук репчатый": (Decimal("100"), None),
    "Чеснок": (Decimal("5"), None),
    "Картофель": (Decimal("150"), None),
    "Морковь": (Decimal("80"), None),
    "Яйцо": (Decimal("55"), None),
    "Помидор": (Decimal("120"), None),
    "Огурец": (Decimal("100"), None),
    "Болгарский перец": (Decimal("150"), None),
    "Яблоко": (Decimal("180"), None),
    "Банан": (Decimal("120"), None),
    "Хлеб цельнозерновой": (Decimal("35"), None),
    "Соль": (None, Decimal("1.200")),
    "Сахар": (None, Decimal("0.850")),
    "Мука пшеничная": (None, Decimal("0.550")),
    "Сливочное масло": (None, Decimal("0.910")),
    "Мёд": (None, Decimal("1.420")),
    "Оливковое масло": (None, Decimal("0.920")),
    "Подсолнечное масло": (None, Decimal("0.920")),
    "Вода": (None, Decimal("1.000")),
}


def upgrade() -> None:
    conn = op.get_bind()
    for name, (piece, density) in _CONVERSIONS.items():
        if piece is not None:
            conn.execute(
                sa.text(
                    """
                    UPDATE ingredients
                    SET grams_per_piece = :piece,
                        updated_at = now()
                    WHERE canonical_name = :name
                      AND grams_per_piece IS NULL
                    """
                ),
                {"name": name, "piece": piece},
            )
        if density is not None:
            conn.execute(
                sa.text(
                    """
                    UPDATE ingredients
                    SET density_g_per_ml = :density,
                        updated_at = now()
                    WHERE canonical_name = :name
                      AND density_g_per_ml IS NULL
                    """
                ),
                {"name": name, "density": density},
            )


def downgrade() -> None:
    # Data backfill — do not null out conversions that may have been curated.
    pass
