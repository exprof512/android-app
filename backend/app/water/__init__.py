"""Water intake domain."""

from app.water.api import router
from app.water.models import WaterEntry

__all__ = ["WaterEntry", "router"]
