"""recipe images

Revision ID: 0006_recipe_images
Revises: 0005_meal_plans
Create Date: 2026-09-21

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_recipe_images"
down_revision: str | Sequence[str] | None = "0005_meal_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = ("recipe_images", "ai_image_usage")


def upgrade() -> None:
    op.create_table(
        "recipe_images",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("thumbnail_storage_key", sa.String(length=1024), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(length=16), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("generation_status", sa.String(length=16), nullable=False),
        sa.Column("generation_error", sa.String(length=512), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_image_id", sa.Uuid(), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id", name="pk_recipe_images"),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_recipe_images_recipe_id_recipes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_image_id"],
            ["recipe_images.id"],
            name="fk_recipe_images_source_image_id_recipe_images",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "generation_status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_recipe_images_generation_status",
        ),
        sa.CheckConstraint(
            "(generation_status <> 'ready') OR "
            "(storage_key IS NOT NULL AND thumbnail_storage_key IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="ck_recipe_images_ready_has_assets",
        ),
    )
    op.create_index(
        "ix_recipe_images_recipe_created",
        "recipe_images",
        ["recipe_id", "created_at"],
    )
    op.create_index(
        "ix_recipe_images_status_updated",
        "recipe_images",
        ["generation_status", "updated_at"],
    )
    op.create_index(
        "uq_recipe_images_primary",
        "recipe_images",
        ["recipe_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )

    op.create_table(
        "ai_image_usage",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_image_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("size", sa.String(length=32), nullable=True),
        sa.Column("quality", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id", name="pk_ai_image_usage"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ai_image_usage_user_id_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_ai_image_usage_recipe_id_recipes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_image_id"],
            ["recipe_images.id"],
            name="fk_ai_image_usage_recipe_image_id_recipe_images",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed', 'reused')",
            name="ck_ai_image_usage_status",
        ),
    )
    op.create_index(
        "ix_ai_image_usage_user_created",
        "ai_image_usage",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_image_usage_model_status_created",
        "ai_image_usage",
        ["model", "status", "created_at"],
    )
    op.create_index(
        "ix_ai_image_usage_recipe_created",
        "ai_image_usage",
        ["recipe_id", "created_at"],
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
    op.drop_index("ix_ai_image_usage_recipe_created", table_name="ai_image_usage")
    op.drop_index("ix_ai_image_usage_model_status_created", table_name="ai_image_usage")
    op.drop_index("ix_ai_image_usage_user_created", table_name="ai_image_usage")
    op.drop_table("ai_image_usage")
    op.drop_index("uq_recipe_images_primary", table_name="recipe_images")
    op.drop_index("ix_recipe_images_status_updated", table_name="recipe_images")
    op.drop_index("ix_recipe_images_recipe_created", table_name="recipe_images")
    op.drop_table("recipe_images")
