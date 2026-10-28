"""recipe owner for copy-on-write substitutions

Revision ID: 0019_recipe_owner
Revises: 0018_phase25b_one_ready_plan
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_recipe_owner"
down_revision = "0018_phase25b_one_ready_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recipes",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_recipes_created_by_user_id_users",
        "recipes",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_recipes_created_by_user_id", "recipes", ["created_by_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_recipes_created_by_user_id", table_name="recipes")
    op.drop_constraint(
        "fk_recipes_created_by_user_id_users", "recipes", type_="foreignkey"
    )
    op.drop_column("recipes", "created_by_user_id")
