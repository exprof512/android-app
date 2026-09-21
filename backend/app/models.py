"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.ai.models import AiTextUsage
from app.auth.models import RefreshToken, User
from app.images.models import AiImageUsage, RecipeImage
from app.meal_plans.models import MealPlan, MealPlanItem
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
    "AiImageUsage",
    "AiTextUsage",
    "AvailableProduct",
    "FoodPreference",
    "FoodRestriction",
    "Goal",
    "Ingredient",
    "MealPlan",
    "MealPlanItem",
    "Recipe",
    "RecipeImage",
    "RecipeIngredient",
    "RefreshToken",
    "User",
    "UserProfile",
    "UserRecipeFavorite",
]
