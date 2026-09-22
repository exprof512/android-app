"""weight entries for progress

Revision ID: 0008_weight_entries
Revises: 0007_shopping_lists
Create Date: 2026-09-22

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_weight_entries"
down_revision: str | Sequence[str] | None = "0007_shopping_lists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weight_entries",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
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
            "weight_kg >= 30 AND weight_kg <= 400",
            name="ck_weight_entries_weight_kg",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weight_entries_user_measured_at",
        "weight_entries",
        ["user_id", sa.text("measured_at DESC")],
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_weight_entries_set_updated_at
            BEFORE UPDATE ON weight_entries
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_weight_entries_set_updated_at ON weight_entries"))
    op.drop_index("ix_weight_entries_user_measured_at", table_name="weight_entries")
    op.drop_table("weight_entries")
