"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.ai.models import AiTextUsage
from app.auth.models import RefreshToken, User
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
    "AiTextUsage",
    "AvailableProduct",
    "FoodPreference",
    "FoodRestriction",
    "Goal",
    "Ingredient",
    "MealPlan",
    "MealPlanItem",
    "Recipe",
    "RecipeIngredient",
    "RefreshToken",
    "User",
    "UserProfile",
    "UserRecipeFavorite",
]
