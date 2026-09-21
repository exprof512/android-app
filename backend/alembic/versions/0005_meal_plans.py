"""meal plans

Revision ID: 0005_meal_plans
Revises: 0004_ai_text_usage
Create Date: 2026-09-21

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_meal_plans"
down_revision: str | Sequence[str] | None = "0004_ai_text_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = ("meal_plans", "meal_plan_items")


def upgrade() -> None:
    op.create_table(
        "meal_plans",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("calorie_target_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_target_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("fat_target_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("carbohydrate_target_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("generation_request_hash", sa.CHAR(length=64), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_meal_plans"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_meal_plans_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"], ["goals.id"], name="fk_meal_plans_goal_id_goals", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'archived')", name="ck_meal_plans_status"
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_meal_plans_date_range"),
        sa.CheckConstraint(
            "calorie_target_kcal > 0 AND protein_target_g >= 0 "
            "AND fat_target_g >= 0 AND carbohydrate_target_g >= 0",
            name="ck_meal_plans_targets_non_negative",
        ),
    )
    op.create_index(
        "ix_meal_plans_user_start_date", "meal_plans", ["user_id", "start_date"]
    )
    op.create_index(
        "ix_meal_plans_user_status_start",
        "meal_plans",
        ["user_id", "status", "start_date"],
    )
    op.create_index(
        "uq_meal_plans_user_generation_request_hash",
        "meal_plans",
        ["user_id", "generation_request_hash"],
        unique=True,
        postgresql_where=sa.text("generation_request_hash IS NOT NULL"),
    )

    op.create_table(
        "meal_plan_items",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("meal_plan_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        sa.Column("servings", sa.Numeric(5, 2), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calories_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("fat_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("carbohydrate_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("estimated_cost_amount", sa.Numeric(12, 2), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_meal_plan_items"),
        sa.ForeignKeyConstraint(
            ["meal_plan_id"],
            ["meal_plans.id"],
            name="fk_meal_plan_items_meal_plan_id_meal_plans",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_meal_plan_items_recipe_id_recipes",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "meal_plan_id",
            "planned_date",
            "meal_type",
            "sort_order",
            name="uq_meal_plan_items_slot",
        ),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_meal_plan_items_meal_type",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'replaced', 'completed', 'skipped')",
            name="ck_meal_plan_items_status",
        ),
        sa.CheckConstraint("servings > 0", name="ck_meal_plan_items_servings"),
        sa.CheckConstraint(
            "calories_kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_meal_plan_items_nutrition_non_negative",
        ),
    )
    op.create_index(
        "ix_meal_plan_items_plan_date",
        "meal_plan_items",
        ["meal_plan_id", "planned_date"],
    )
    op.create_index("ix_meal_plan_items_recipe_id", "meal_plan_items", ["recipe_id"])

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
    op.drop_index("ix_meal_plan_items_recipe_id", table_name="meal_plan_items")
    op.drop_index("ix_meal_plan_items_plan_date", table_name="meal_plan_items")
    op.drop_table("meal_plan_items")
    op.drop_index(
        "uq_meal_plans_user_generation_request_hash", table_name="meal_plans"
    )
    op.drop_index("ix_meal_plans_user_status_start", table_name="meal_plans")
    op.drop_index("ix_meal_plans_user_start_date", table_name="meal_plans")
    op.drop_table("meal_plans")
