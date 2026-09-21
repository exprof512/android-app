"""Model registry so Alembic autogenerate sees every table in ``Base.metadata``."""

from app.auth.models import RefreshToken, User

__all__ = ["RefreshToken", "User"]
