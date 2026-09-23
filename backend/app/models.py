"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.ai.models import AiTextUsage
from app.analytics.models import ProductEvent
from app.auth.models import (
    EmailVerificationToken,
    IdempotencyKey,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.chat.models import AiConversation, AiMessage
from app.entitlements.models import Subscription, UsageLimit
from app.images.models import AiImageUsage, RecipeImage
from app.meal_plans.models import MealPlan, MealPlanItem
from app.nutrition.models import NutritionLog
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)
from app.progress.models import WeightEntry
from app.recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    UserRecipeFavorite,
)
from app.shopping.models import ShoppingList, ShoppingListItem
from app.water.models import WaterEntry

__all__ = [
    "AiConversation",
    "AiImageUsage",
    "AiMessage",
    "AiTextUsage",
    "AvailableProduct",
    "EmailVerificationToken",
    "FoodPreference",
    "FoodRestriction",
    "Goal",
    "IdempotencyKey",
    "Ingredient",
    "MealPlan",
    "MealPlanItem",
    "NutritionLog",
    "PasswordResetToken",
    "ProductEvent",
    "Recipe",
    "RecipeImage",
    "RecipeIngredient",
    "RefreshToken",
    "ShoppingList",
    "ShoppingListItem",
    "Subscription",
    "UsageLimit",
    "User",
    "UserProfile",
    "UserRecipeFavorite",
    "WaterEntry",
    "WeightEntry",
]
