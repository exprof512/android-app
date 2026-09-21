"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.auth.models import RefreshToken, User
from app.profiles.models import (
    AvailableProduct,
    FoodPreference,
    FoodRestriction,
    Goal,
    UserProfile,
)

__all__ = [
    "AvailableProduct",
    "FoodPreference",
    "FoodRestriction",
    "Goal",
    "RefreshToken",
    "User",
    "UserProfile",
]
