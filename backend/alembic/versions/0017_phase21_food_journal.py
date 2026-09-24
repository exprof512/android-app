"""Phase 21: extend nutrition_logs + meal_templates

Revision ID: 0017_phase21_food_journal
Revises: 0016_ingredient_unit_conversions
Create Date: 2026-09-24

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_phase21_food_journal"
down_revision: str | Sequence[str] | None = "0016_ingredient_unit_conversions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop old check constraints and recreate with extended enums.
    op.drop_constraint("ck_nutrition_logs_meal_type", "nutrition_logs", type_="check")
    op.drop_constraint("ck_nutrition_logs_source", "nutrition_logs", type_="check")
    op.create_check_constraint(
        "ck_nutrition_logs_meal_type",
        "nutrition_logs",
        "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'custom')",
    )
    op.create_check_constraint(
        "ck_nutrition_logs_source",
        "nutrition_logs",
        "source IN ("
        "'meal_plan_item', 'recipe', 'manual', "
        "'photo_ai', 'search', 'quick_add', 'planned_meal'"
        ")",
    )

    op.add_column(
        "nutrition_logs",
        sa.Column("ingredient_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_nutrition_logs_ingredient_id",
        "nutrition_logs",
        "ingredients",
        ["ingredient_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "nutrition_logs",
        sa.Column("quantity_g", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "nutrition_logs",
        sa.Column("unit", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "nutrition_logs",
        sa.Column("notes", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "nutrition_logs",
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=True),
    )

    op.create_table(
        "meal_templates",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
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
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'custom')",
            name="ck_meal_templates_meal_type",
        ),
    )
    op.create_index(
        "ix_meal_templates_user_id", "meal_templates", ["user_id"]
    )

    op.create_table(
        "meal_template_items",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
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
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("recipe_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity_g", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("servings", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["meal_templates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("servings > 0", name="ck_meal_template_items_servings"),
    )


def downgrade() -> None:
    op.drop_table("meal_template_items")
    op.drop_index("ix_meal_templates_user_id", table_name="meal_templates")
    op.drop_table("meal_templates")
    op.drop_column("nutrition_logs", "confidence")
    op.drop_column("nutrition_logs", "notes")
    op.drop_column("nutrition_logs", "unit")
    op.drop_column("nutrition_logs", "quantity_g")
    op.drop_constraint(
        "fk_nutrition_logs_ingredient_id", "nutrition_logs", type_="foreignkey"
    )
    op.drop_column("nutrition_logs", "ingredient_id")
    op.drop_constraint("ck_nutrition_logs_meal_type", "nutrition_logs", type_="check")
    op.drop_constraint("ck_nutrition_logs_source", "nutrition_logs", type_="check")
    op.create_check_constraint(
        "ck_nutrition_logs_meal_type",
        "nutrition_logs",
        "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
    )
    op.create_check_constraint(
        "ck_nutrition_logs_source",
        "nutrition_logs",
        "source IN ('meal_plan_item', 'recipe', 'manual')",
    )
