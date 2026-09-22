"""Expand ingredient catalog and add entitlements tables.

Revision ID: 0010_entitlements_ingredients
Revises: 0009_ai_chat
Create Date: 2026-09-22

"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision: str = "0010_entitlements_ingredients"
down_revision: str | Sequence[str] | None = "0009_ai_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Extra catalog rows common in AI meal proposals (canonical, normalized, unit, kcal, P, F, C, price, g/piece, density)
EXTRA_INGREDIENTS: tuple[tuple, ...] = (
    ("Киноа", "киноа", "g", 120, 4.4, 1.9, 21.3, 45, None, None),
    ("Кускус", "кускус", "g", 112, 3.8, 0.2, 23, 18, None, None),
    ("Авокадо", "авокадо", "g", 160, 2, 15, 9, 80, 200, None),
    ("Кабачок", "кабачок", "g", 17, 1.2, 0.3, 3.1, 12, None, None),
    ("Шампиньоны", "шампиньоны", "g", 27, 3.1, 0.3, 3.3, 40, None, None),
    ("Чеснок", "чеснок", "g", 149, 6.5, 0.5, 33, 25, 5, None),
    ("Петрушка", "петрушка", "g", 36, 3, 0.8, 6.3, 30, None, None),
    ("Укроп", "укроп", "g", 43, 3.5, 1.1, 7, 30, None, None),
    ("Базилик", "базилик", "g", 23, 3.2, 0.6, 2.7, 50, None, None),
    ("Лимон", "лимон", "g", 29, 1.1, 0.3, 9, 15, 100, None),
    ("Сметана", "сметана", "g", 206, 2.8, 20, 3.2, 25, None, None),
    ("Томатная паста", "томатная паста", "g", 82, 4.3, 0.5, 19, 20, None, None),
    ("Соевый соус", "соевый соус", "ml", 53, 8.1, 0.1, 4.9, 15, None, 1.15),
    ("Нут", "нут", "g", 364, 19, 6, 61, 20, None, None),
    ("Булгур", "булгур", "g", 342, 12, 1.3, 76, 15, None, None),
    ("Батат", "батат", "g", 86, 1.6, 0.1, 20, 18, None, None),
    ("Кукуруза", "кукуруза", "g", 96, 3.4, 1.5, 19, 15, None, None),
    ("Имбирь", "имбирь", "g", 80, 1.8, 0.8, 18, 60, None, None),
)


def upgrade() -> None:
    ingredients = sa.table(
        "ingredients",
        sa.column("canonical_name", sa.String),
        sa.column("normalized_name", sa.String),
        sa.column("default_unit", sa.String),
        sa.column("calories_per_100g", sa.Numeric),
        sa.column("protein_per_100g", sa.Numeric),
        sa.column("fat_per_100g", sa.Numeric),
        sa.column("carbohydrate_per_100g", sa.Numeric),
        sa.column("reference_price_per_100g", sa.Numeric),
        sa.column("grams_per_piece", sa.Numeric),
        sa.column("density_g_per_ml", sa.Numeric),
        sa.column("source", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("currency", sa.String),
    )
    op.bulk_insert(
        ingredients,
        [
            {
                "canonical_name": name,
                "normalized_name": normalized,
                "default_unit": unit,
                "calories_per_100g": Decimal(str(kcal)),
                "protein_per_100g": Decimal(str(protein)),
                "fat_per_100g": Decimal(str(fat)),
                "carbohydrate_per_100g": Decimal(str(carbs)),
                "reference_price_per_100g": (
                    None if price is None else Decimal(str(price))
                ),
                "grams_per_piece": (
                    None if grams_piece is None else Decimal(str(grams_piece))
                ),
                "density_g_per_ml": (
                    None if density is None else Decimal(str(density))
                ),
                "source": "seed",
                "is_active": True,
                "currency": None if price is None else "RUB",
            }
            for (
                name,
                normalized,
                unit,
                kcal,
                protein,
                fat,
                carbs,
                price,
                grams_piece,
                density,
            ) in EXTRA_INGREDIENTS
        ],
    )

    op.create_table(
        "subscriptions",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
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
            "tier IN ('free', 'premium')", name="ck_subscriptions_tier"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'canceled', 'expired', 'past_due')",
            name="ck_subscriptions_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"]
    )
    op.create_index(
        "uq_subscriptions_provider_sub",
        "subscriptions",
        ["provider", "provider_subscription_id"],
        unique=True,
        postgresql_where=sa.text(
            "provider IS NOT NULL AND provider_subscription_id IS NOT NULL"
        ),
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_subscriptions_set_updated_at
            BEFORE UPDATE ON subscriptions
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
            """
        )
    )

    op.create_table(
        "usage_limits",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("limit_value", sa.Integer(), nullable=False),
        sa.Column("used_value", sa.Integer(), server_default=sa.text("0"), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "feature", "window_start", name="uq_usage_limits_window"
        ),
    )
    op.create_index(
        "ix_usage_limits_user_feature_window_end",
        "usage_limits",
        ["user_id", "feature", "window_end"],
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_usage_limits_set_updated_at
            BEFORE UPDATE ON usage_limits
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_usage_limits_set_updated_at ON usage_limits"))
    op.drop_index(
        "ix_usage_limits_user_feature_window_end", table_name="usage_limits"
    )
    op.drop_table("usage_limits")
    op.execute(
        sa.text("DROP TRIGGER IF EXISTS trg_subscriptions_set_updated_at ON subscriptions")
    )
    op.drop_index("uq_subscriptions_provider_sub", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    for _, normalized, *_ in EXTRA_INGREDIENTS:
        op.execute(
            sa.text("DELETE FROM ingredients WHERE normalized_name = :n").bindparams(
                n=normalized
            )
        )
