"""nutrition logs, policy version, ingredient source_version

Revision ID: 0013_nutrition_diary_policy
Revises: 0012_product_events
Create Date: 2026-09-23

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_nutrition_diary_policy"
down_revision: str | Sequence[str] | None = "0012_product_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column(
            "nutrition_policy_version",
            sa.String(length=32),
            server_default=sa.text("'v1'"),
            nullable=False,
        ),
    )
    op.add_column(
        "meal_plans",
        sa.Column(
            "nutrition_policy_version",
            sa.String(length=32),
            server_default=sa.text("'v1'"),
            nullable=False,
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column("source_version", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE ingredients SET source_version = 'seed-v1' WHERE source = 'seed'")

    op.create_table(
        "nutrition_logs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("logged_on", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("meal_plan_item_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("calories_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("carbohydrate_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("servings", sa.Numeric(precision=5, scale=2), server_default=sa.text("1"), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_nutrition_logs_meal_type",
        ),
        sa.CheckConstraint(
            "source IN ('meal_plan_item', 'recipe', 'manual')",
            name="ck_nutrition_logs_source",
        ),
        sa.CheckConstraint("calories_kcal >= 0", name="ck_nutrition_logs_calories"),
        sa.CheckConstraint(
            "protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_nutrition_logs_macros",
        ),
        sa.CheckConstraint("servings > 0", name="ck_nutrition_logs_servings"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["meal_plan_item_id"], ["meal_plan_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutrition_logs_user_logged_on",
        "nutrition_logs",
        ["user_id", "logged_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_nutrition_logs_user_logged_on", table_name="nutrition_logs")
    op.drop_table("nutrition_logs")
    op.drop_column("ingredients", "source_version")
    op.drop_column("meal_plans", "nutrition_policy_version")
    op.drop_column("goals", "nutrition_policy_version")
