"""ai text usage

Revision ID: 0004_ai_text_usage
Revises: 0003_recipe_domain
Create Date: 2026-09-21

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_ai_text_usage"
down_revision: str | Sequence[str] | None = "0003_recipe_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = ("ai_text_usage",)


def upgrade() -> None:
    op.create_table(
        "ai_text_usage",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("request_fingerprint", sa.CHAR(length=64), nullable=True),
        sa.Column("schema_version", sa.SmallInteger(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_ai_text_usage"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ai_text_usage_user_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'cached', 'failed', 'invalid', 'reused')",
            name="ck_ai_text_usage_status",
        ),
    )
    op.create_index(
        "ix_ai_text_usage_user_created",
        "ai_text_usage",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_text_usage_operation_model_created",
        "ai_text_usage",
        ["operation", "model", "created_at"],
    )
    for table in TIMESTAMP_TABLES:
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER trg_{table}_set_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION set_updated_at()
                """
            )
        )


def downgrade() -> None:
    for table in TIMESTAMP_TABLES:
        op.execute(
            sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table}")
        )
    op.drop_index(
        "ix_ai_text_usage_operation_model_created", table_name="ai_text_usage"
    )
    op.drop_index("ix_ai_text_usage_user_created", table_name="ai_text_usage")
    op.drop_table("ai_text_usage")
