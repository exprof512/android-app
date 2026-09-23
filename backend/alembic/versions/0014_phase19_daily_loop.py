"""water entries + shopping stale/fingerprint + nutrition unique

Revision ID: 0014_phase19_daily_loop
Revises: 0013_nutrition_diary_policy
Create Date: 2026-09-23

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_phase19_daily_loop"
down_revision: str | Sequence[str] | None = "0013_nutrition_diary_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "water_entries",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("amount_ml", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_ml > 0", name="ck_water_entries_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_water_entries_user_recorded_on",
        "water_entries",
        ["user_id", "recorded_on"],
    )

    op.add_column(
        "shopping_lists",
        sa.Column(
            "stale",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "shopping_lists",
        sa.Column("plan_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "shopping_lists",
        sa.Column("estimated_total_amount", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "shopping_lists",
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'RUB'"),
            nullable=False,
        ),
    )

    op.create_index(
        "uq_nutrition_logs_meal_plan_item",
        "nutrition_logs",
        ["meal_plan_item_id"],
        unique=True,
        postgresql_where=sa.text("meal_plan_item_id IS NOT NULL"),
        sqlite_where=sa.text("meal_plan_item_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_nutrition_logs_meal_plan_item",
        table_name="nutrition_logs",
    )
    op.drop_column("shopping_lists", "currency")
    op.drop_column("shopping_lists", "estimated_total_amount")
    op.drop_column("shopping_lists", "plan_fingerprint")
    op.drop_column("shopping_lists", "stale")
    op.drop_index("ix_water_entries_user_recorded_on", table_name="water_entries")
    op.drop_table("water_entries")
