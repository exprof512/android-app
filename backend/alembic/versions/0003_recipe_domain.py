"""recipe domain

Revision ID: 0003_recipe_domain
Revises: 0002_profile_and_nutrition
Create Date: 2026-09-21

"""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0003_recipe_domain"
down_revision: str | Sequence[str] | None = "0002_profile_and_nutrition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_TABLES = ("ingredients", "recipes", "recipe_ingredients")

# Approximate public reference values per 100 g, priced in RUB. Marked source
# 'seed' so a curated dataset can replace them without touching recipes.
# name, normalized, unit, kcal, protein, fat, carbohydrate, price, piece_g, density
SEED_INGREDIENTS: tuple[tuple, ...] = (
    ("Куриная грудка", "куриная грудка", "g", 165, 31, 3.6, 0, 45, None, None),
    ("Индейка", "индейка", "g", 189, 29, 7, 0, 60, None, None),
    ("Говядина", "говядина", "g", 250, 26, 15, 0, 75, None, None),
    ("Свинина", "свинина", "g", 242, 27, 14, 0, 55, None, None),
    ("Лосось", "лосось", "g", 208, 20, 13, 0, 120, None, None),
    ("Треска", "треска", "g", 82, 18, 0.7, 0, 55, None, None),
    ("Креветки", "креветки", "g", 99, 24, 0.3, 0.2, 120, None, None),
    ("Яйцо", "яйцо", "piece", 157, 13, 11, 1.1, 12, 55, None),
    ("Молоко", "молоко", "ml", 60, 3.2, 3.2, 4.8, 9, None, 1.03),
    ("Кефир", "кефир", "ml", 51, 3.4, 2, 4.1, 9, None, 1.03),
    ("Творог", "творог", "g", 121, 17, 5, 3, 30, None, None),
    ("Греческий йогурт", "греческий йогурт", "g", 59, 10, 0.4, 3.6, 35, None, None),
    ("Сыр твёрдый", "сыр твердый", "g", 364, 25, 30, 2, 90, None, None),
    ("Тофу", "тофу", "g", 76, 8, 4.8, 1.9, 60, None, None),
    ("Гречка", "гречка", "g", 343, 13, 3.4, 62, 12, None, None),
    ("Рис", "рис", "g", 344, 7, 1, 78, 10, None, None),
    ("Овсяные хлопья", "овсяные хлопья", "g", 366, 12, 7, 62, 11, None, None),
    ("Макароны", "макароны", "g", 344, 11, 1.3, 70, 12, None, None),
    ("Мука пшеничная", "мука пшеничная", "g", 364, 10, 1, 76, 6, None, None),
    ("Хлеб цельнозерновой", "хлеб цельнозерновой", "g", 247, 9, 3.4, 46, 12, 35, None),
    ("Фасоль", "фасоль", "g", 333, 21, 1.2, 60, 15, None, None),
    ("Чечевица", "чечевица", "g", 352, 24, 1, 63, 18, None, None),
    ("Картофель", "картофель", "g", 77, 2, 0.4, 17, 5, None, None),
    ("Морковь", "морковь", "g", 41, 0.9, 0.2, 10, 6, None, None),
    ("Лук репчатый", "лук репчатый", "g", 40, 1.1, 0.1, 9, 5, None, None),
    ("Капуста белокочанная", "капуста белокочанная", "g", 25, 1.3, 0.1, 5.8, 5, None, None),
    ("Брокколи", "брокколи", "g", 34, 2.8, 0.4, 7, 25, None, None),
    ("Шпинат", "шпинат", "g", 23, 2.9, 0.4, 3.6, 40, None, None),
    ("Помидор", "помидор", "g", 18, 0.9, 0.2, 3.9, 20, 120, None),
    ("Огурец", "огурец", "g", 15, 0.7, 0.1, 3.6, 18, 100, None),
    ("Болгарский перец", "болгарский перец", "g", 27, 1, 0.3, 6, 25, 150, None),
    ("Яблоко", "яблоко", "g", 52, 0.3, 0.2, 14, 12, 180, None),
    ("Банан", "банан", "g", 89, 1.1, 0.3, 23, 11, 120, None),
    ("Черника", "черника", "g", 57, 0.7, 0.3, 14, 90, None, None),
    ("Миндаль", "миндаль", "g", 579, 21, 50, 22, 150, None, None),
    ("Арахис", "арахис", "g", 567, 26, 49, 16, 40, None, None),
    ("Оливковое масло", "оливковое масло", "ml", 884, 0, 100, 0, 90, None, 0.92),
    ("Подсолнечное масло", "подсолнечное масло", "ml", 899, 0, 100, 0, 15, None, 0.92),
    ("Сливочное масло", "сливочное масло", "g", 717, 0.9, 81, 0.7, 90, None, None),
    ("Мёд", "мед", "g", 304, 0.3, 0, 82, 60, None, 1.42),
    ("Сахар", "сахар", "g", 387, 0, 0, 100, 6, None, None),
    ("Соль", "соль", "g", 0, 0, 0, 0, 2, None, None),
    ("Вода", "вода", "ml", 0, 0, 0, 0, None, None, 1.0),
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
    ingredients = op.create_table(
        "ingredients",
        *_identity_columns(),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("default_unit", sa.String(length=16), nullable=False),
        sa.Column("calories_per_100g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("protein_per_100g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("fat_per_100g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "carbohydrate_per_100g", sa.Numeric(precision=8, scale=2), nullable=False
        ),
        sa.Column(
            "reference_price_per_100g", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column("currency", sa.CHAR(length=3), nullable=True),
        sa.Column("grams_per_piece", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("density_g_per_ml", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column(
            "source", sa.String(length=32), server_default=sa.text("'seed'"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.CheckConstraint(
            "default_unit IN ('g', 'kg', 'ml', 'l', 'tbsp', 'tsp', 'piece')",
            name="ck_ingredients_default_unit",
        ),
        sa.CheckConstraint(
            "source IN ('seed', 'curated', 'import')", name="ck_ingredients_source"
        ),
        sa.CheckConstraint(
            "calories_per_100g >= 0 AND protein_per_100g >= 0 "
            "AND fat_per_100g >= 0 AND carbohydrate_per_100g >= 0",
            name="ck_ingredients_nutrition_non_negative",
        ),
        sa.CheckConstraint(
            "reference_price_per_100g IS NULL OR reference_price_per_100g >= 0",
            name="ck_ingredients_reference_price_non_negative",
        ),
        sa.CheckConstraint(
            "grams_per_piece IS NULL OR grams_per_piece > 0",
            name="ck_ingredients_grams_per_piece",
        ),
        sa.CheckConstraint(
            "density_g_per_ml IS NULL OR density_g_per_ml > 0",
            name="ck_ingredients_density",
        ),
        sa.CheckConstraint(
            "reference_price_per_100g IS NULL OR currency IS NOT NULL",
            name="ck_ingredients_price_needs_currency",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingredients"),
        sa.UniqueConstraint("normalized_name", name="uq_ingredients_normalized_name"),
    )

    op.create_table(
        "recipes",
        *_identity_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recipe_fingerprint", sa.CHAR(length=64), nullable=False),
        sa.Column("cooking_method", sa.String(length=64), nullable=False),
        sa.Column("cook_time_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("servings", sa.SmallInteger(), nullable=False),
        sa.Column("calories_kcal", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("carbohydrate_g", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "estimated_cost_amount", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column(
            "steps",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'ready'"), nullable=False
        ),
        sa.Column("ai_model", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "cooking_method IN "
            "('boil', 'fry', 'bake', 'stew', 'grill', 'steam', 'raw', 'mixed')",
            name="ck_recipes_cooking_method",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'archived')", name="ck_recipes_status"
        ),
        sa.CheckConstraint(
            "cook_time_minutes BETWEEN 1 AND 600", name="ck_recipes_cook_time_minutes"
        ),
        sa.CheckConstraint("servings BETWEEN 1 AND 12", name="ck_recipes_servings"),
        sa.CheckConstraint(
            "calories_kcal >= 0 AND protein_g >= 0 AND fat_g >= 0 AND carbohydrate_g >= 0",
            name="ck_recipes_nutrition_non_negative",
        ),
        sa.CheckConstraint(
            "estimated_cost_amount >= 0", name="ck_recipes_estimated_cost_non_negative"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recipes"),
        sa.UniqueConstraint("recipe_fingerprint", name="uq_recipes_recipe_fingerprint"),
    )
    op.create_index(
        "ix_recipes_status_updated_at",
        "recipes",
        ["status", sa.literal_column("updated_at DESC")],
    )

    op.create_table(
        "recipe_ingredients",
        *_identity_columns(),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("quantity_g", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantity_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("cost_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "unit IN ('g', 'kg', 'ml', 'l', 'tbsp', 'tsp', 'piece')",
            name="ck_recipe_ingredients_unit",
        ),
        sa.CheckConstraint("quantity_g > 0", name="ck_recipe_ingredients_quantity_g"),
        sa.CheckConstraint(
            "quantity_value > 0", name="ck_recipe_ingredients_quantity_value"
        ),
        sa.CheckConstraint(
            "cost_amount IS NULL OR cost_amount >= 0",
            name="ck_recipe_ingredients_cost_amount",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_recipe_ingredients_recipe_id_recipes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ingredients.id"],
            name="fk_recipe_ingredients_ingredient_id_ingredients",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recipe_ingredients"),
        sa.UniqueConstraint(
            "recipe_id", "sort_order", name="uq_recipe_ingredients_sort_order"
        ),
    )
    op.create_index(
        "ix_recipe_ingredients_ingredient_id", "recipe_ingredients", ["ingredient_id"]
    )

    op.create_table(
        "user_recipe_favorites",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_recipe_favorites_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"],
            ["recipes.id"],
            name="fk_user_recipe_favorites_recipe_id_recipes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "recipe_id", name="pk_user_recipe_favorites"),
    )
    op.create_index(
        "ix_user_recipe_favorites_user_id_created_at",
        "user_recipe_favorites",
        ["user_id", sa.literal_column("created_at DESC")],
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

    op.bulk_insert(
        ingredients,
        [
            {
                "canonical_name": canonical_name,
                "normalized_name": normalized_name,
                "default_unit": unit,
                "calories_per_100g": Decimal(str(calories)),
                "protein_per_100g": Decimal(str(protein)),
                "fat_per_100g": Decimal(str(fat)),
                "carbohydrate_per_100g": Decimal(str(carbohydrate)),
                "reference_price_per_100g": (
                    None if price is None else Decimal(str(price))
                ),
                "currency": None if price is None else "RUB",
                "grams_per_piece": None if piece is None else Decimal(str(piece)),
                "density_g_per_ml": None if density is None else Decimal(str(density)),
                "source": "seed",
                "is_active": True,
            }
            for (
                canonical_name,
                normalized_name,
                unit,
                calories,
                protein,
                fat,
                carbohydrate,
                price,
                piece,
                density,
            ) in SEED_INGREDIENTS
        ],
    )


def downgrade() -> None:
    for table in TIMESTAMP_TABLES:
        op.execute(
            sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table}")
        )

    op.drop_index(
        "ix_user_recipe_favorites_user_id_created_at", table_name="user_recipe_favorites"
    )
    op.drop_table("user_recipe_favorites")
    op.drop_index("ix_recipe_ingredients_ingredient_id", table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")
    op.drop_index("ix_recipes_status_updated_at", table_name="recipes")
    op.drop_table("recipes")
    op.drop_table("ingredients")
