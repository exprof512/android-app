"""ai_recommendation_records

Revision ID: 0015_ai_recommendation_records
Revises: 0014_phase19_daily_loop
Create Date: 2026-09-24

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_ai_recommendation_records"
down_revision: str | Sequence[str] | None = "0014_phase19_daily_loop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_recommendation_records",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("context_version", sa.String(length=16), nullable=True),
        sa.Column("prompt_version", sa.String(length=16), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'selected', 'rejected', 'failed')",
            name="ck_ai_recommendation_records_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_recommendation_records_user_created",
        "ai_recommendation_records",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_recommendation_records_user_created",
        table_name="ai_recommendation_records",
    )
    op.drop_table("ai_recommendation_records")
