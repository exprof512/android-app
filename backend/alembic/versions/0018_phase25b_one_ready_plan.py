"""One ready plan per user-day.

Revision ID: 0018_phase25b_one_ready_plan
Revises: 0017_phase21_food_journal
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018_phase25b_one_ready_plan"
down_revision: str | Sequence[str] | None = "0017_phase21_food_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.meal_plans.overlap import collapse_ready_overlaps

    collapse_ready_overlaps(op.get_bind())
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE meal_plans
        ADD CONSTRAINT excl_meal_plans_one_ready_per_day
        EXCLUDE USING gist (
            user_id WITH =,
            daterange(start_date, end_date, '[]') WITH &&
        )
        WHERE (status = 'ready')
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE meal_plans DROP CONSTRAINT IF EXISTS excl_meal_plans_one_ready_per_day"
    )
