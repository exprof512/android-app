"""profile and nutrition targets

Revision ID: 0002_profile_and_nutrition
Revises: 0001_auth_and_session
Create Date: 2026-09-21

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_profile_and_nutrition"
down_revision: str | Sequence[str] | None = "0001_auth_and_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = (
    "user_profiles",
    "goals",
    "food_preferences",
    "food_restrictions",
    "available_products",
)


def _identity_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "goals",
        *_identity_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_type", sa.String(length=32), nullable=False),
        sa.Column("start_weight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("target_weight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "desired_weekly_change_kg", sa.Numeric(precision=4, scale=2), nullable=True
        ),
        sa.Column("calorie_target_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_target_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("fat_target_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "carbohydrate_target_g", sa.Numeric(precision=8, scale=2), nullable=False
        ),
        sa.Column("bmr_kcal", sa.Integer(), nullable=False),
        sa.Column("tdee_kcal", sa.Integer(), nullable=False),
        sa.Column("safety_floor_kcal", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.Date(), nullable=True),
        sa.Column("ended_at", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "goal_type IN ('lose_weight', 'maintain_weight', 'gain_weight')",
            name="ck_goals_goal_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')", name="ck_goals_status"
        ),
        sa.CheckConstraint(
            "desired_weekly_change_kg IS NULL OR desired_weekly_change_kg BETWEEN 0 AND 2",
            name="ck_goals_desired_weekly_change_kg",
        ),
        sa.CheckConstraint("calorie_target_kcal > 0", name="ck_goals_calorie_target_kcal"),
        sa.CheckConstraint("safety_floor_kcal > 0", name="ck_goals_safety_floor_kcal"),
        sa.CheckConstraint(
            "protein_target_g >= 0 AND fat_target_g >= 0 AND carbohydrate_target_g >= 0",
            name="ck_goals_macro_targets",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_goals_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_goals"),
    )
    op.create_index(
        "ix_goals_user_id_status_started_at",
        "goals",
        ["user_id", "status", sa.literal_column("started_at DESC")],
    )
    op.create_index(
        "uq_goals_active_per_user",
        "goals",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "user_profiles",
        *_identity_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("age_years", sa.SmallInteger(), nullable=True),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("current_weight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("activity_level", sa.String(length=32), nullable=True),
        sa.Column("meals_per_day", sa.SmallInteger(), nullable=True),
        sa.Column("daily_calorie_mode", sa.String(length=16), nullable=True),
        sa.Column("daily_calorie_value", sa.Integer(), nullable=True),
        sa.Column(
            "grocery_budget_weekly", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column("currency", sa.CHAR(length=3), nullable=True),
        sa.Column("max_cook_time_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("household_size", sa.SmallInteger(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("active_goal_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "sex IS NULL OR sex IN ('female', 'male', 'other')", name="ck_user_profiles_sex"
        ),
        sa.CheckConstraint(
            "activity_level IS NULL OR activity_level IN "
            "('sedentary', 'light', 'moderate', 'high', 'very_high')",
            name="ck_user_profiles_activity_level",
        ),
        sa.CheckConstraint(
            "daily_calorie_mode IS NULL OR daily_calorie_mode IN "
            "('auto', 'deficit', 'surplus', 'target')",
            name="ck_user_profiles_daily_calorie_mode",
        ),
        sa.CheckConstraint(
            "age_years IS NULL OR age_years BETWEEN 14 AND 120",
            name="ck_user_profiles_age_years",
        ),
        sa.CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 100 AND 250",
            name="ck_user_profiles_height_cm",
        ),
        sa.CheckConstraint(
            "current_weight_kg IS NULL OR current_weight_kg BETWEEN 30 AND 400",
            name="ck_user_profiles_current_weight_kg",
        ),
        sa.CheckConstraint(
            "meals_per_day IS NULL OR meals_per_day BETWEEN 1 AND 8",
            name="ck_user_profiles_meals_per_day",
        ),
        sa.CheckConstraint(
            "daily_calorie_value IS NULL OR daily_calorie_value BETWEEN 1 AND 10000",
            name="ck_user_profiles_daily_calorie_value",
        ),
        sa.CheckConstraint(
            "grocery_budget_weekly IS NULL OR grocery_budget_weekly >= 0",
            name="ck_user_profiles_grocery_budget_weekly",
        ),
        sa.CheckConstraint(
            "max_cook_time_minutes IS NULL OR max_cook_time_minutes BETWEEN 5 AND 240",
            name="ck_user_profiles_max_cook_time_minutes",
        ),
        sa.CheckConstraint(
            "household_size IS NULL OR household_size BETWEEN 1 AND 20",
            name="ck_user_profiles_household_size",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["active_goal_id"],
            ["goals.id"],
            name="fk_user_profiles_active_goal_id_goals",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    op.create_table(
        "food_preferences",
        *_identity_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_food_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("preference_type", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "preference_type IN ('liked', 'disliked')",
            name="ck_food_preferences_preference_type",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_food_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_preferences"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_food_name",
            "preference_type",
            name="uq_food_preferences_user_name_type",
        ),
    )

    op.create_table(
        "food_restrictions",
        *_identity_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_food_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("restriction_type", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.CheckConstraint(
            "restriction_type IN ('allergy', 'excluded', 'dietary')",
            name="ck_food_restrictions_restriction_type",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_food_restrictions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_food_restrictions"),
        sa.UniqueConstraint(
            "user_id",
            "normalized_food_name",
            "restriction_type",
            name="uq_food_restrictions_user_name_type",
        ),
    )

    op.create_table(
        "available_products",
        *_identity_columns(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        # The foreign key to ingredients arrives with the Phase 4 catalog.
        sa.Column("ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("quantity_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "unit IN ('g', 'kg', 'ml', 'l', 'piece', 'pack', 'tbsp', 'tsp')",
            name="ck_available_products_unit",
        ),
        sa.CheckConstraint(
            "quantity_value > 0", name="ck_available_products_quantity_value"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_available_products_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_available_products"),
    )
    op.create_index(
        "ix_available_products_user_id_normalized_name",
        "available_products",
        ["user_id", "normalized_name"],
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

    # Every user owns exactly one profile row, including accounts from Phase 2.
    op.execute(
        sa.text("INSERT INTO user_profiles (user_id) SELECT id FROM users")
    )


def downgrade() -> None:
    for table in TIMESTAMP_TABLES:
        op.execute(
            sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table}")
        )

    op.drop_index(
        "ix_available_products_user_id_normalized_name", table_name="available_products"
    )
    op.drop_table("available_products")
    op.drop_table("food_restrictions")
    op.drop_table("food_preferences")
    op.drop_table("user_profiles")
    op.drop_index(
        "uq_goals_active_per_user",
        table_name="goals",
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.drop_index("ix_goals_user_id_status_started_at", table_name="goals")
    op.drop_table("goals")
