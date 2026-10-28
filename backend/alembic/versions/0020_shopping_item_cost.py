"""per-item shopping cost

Revision ID: 0020_shopping_item_cost
Revises: 0019_recipe_owner
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_shopping_item_cost"
down_revision = "0019_recipe_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopping_list_items",
        sa.Column("estimated_cost_amount", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shopping_list_items", "estimated_cost_amount")
