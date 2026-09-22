"""shopping lists

Revision ID: 0007_shopping_lists
Revises: 0006_recipe_images
Create Date: 2026-09-22

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_shopping_lists"
down_revision: str | Sequence[str] | None = "0006_recipe_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = ("shopping_lists", "shopping_list_items")


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("meal_plan_id", sa.Uuid(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
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
        sa.CheckConstraint(
            "status IN ('ready', 'archived')", name="ck_shopping_lists_status"
        ),
        sa.CheckConstraint("to_date >= from_date", name="ck_shopping_lists_date_range"),
        sa.ForeignKeyConstraint(
            ["meal_plan_id"], ["meal_plans.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shopping_lists_user_updated_at",
        "shopping_lists",
        ["user_id", "updated_at"],
    )

    op.create_table(
        "shopping_list_items",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("shopping_list_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("quantity_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column(
            "is_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_recipe_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
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
        sa.CheckConstraint("quantity_value > 0", name="ck_shopping_list_items_quantity"),
        sa.CheckConstraint(
            "unit IN ('g', 'kg', 'ml', 'l', 'piece', 'pack', 'tbsp', 'tsp')",
            name="ck_shopping_list_items_unit",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shopping_list_id",
            "normalized_name",
            "unit",
            name="uq_shopping_list_items_name_unit",
        ),
    )
    op.create_index(
        "ix_shopping_list_items_list_id",
        "shopping_list_items",
        ["shopping_list_id"],
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
    op.drop_index("ix_shopping_list_items_list_id", table_name="shopping_list_items")
    op.drop_table("shopping_list_items")
    op.drop_index("ix_shopping_lists_user_updated_at", table_name="shopping_lists")
    op.drop_table("shopping_lists")
