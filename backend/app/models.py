"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.auth.models import RefreshToken, User
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from app.recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    UserRecipeFavorite,
)

__all__ = [
    "AvailableProduct",
    "FoodPreference",
    "FoodRestriction",
    "Goal",
    "Ingredient",
    "Recipe",
    "RecipeIngredient",
    "RefreshToken",
    "User",
    "UserProfile",
    "UserRecipeFavorite",
]
