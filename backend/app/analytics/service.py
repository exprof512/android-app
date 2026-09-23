"""Privacy-safe product analytics."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.models import ProductEvent
from app.core.errors import ApiError
from app.core.models import utcnow
from app.core.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

ALLOWED_EVENTS = frozenset(
    {
        "app_opened",
        "registration_started",
        "registration_completed",
        "login_completed",
        "onboarding_started",
        "onboarding_completed",
        "plan_generation_started",
        "plan_generation_completed",
        "plan_generation_failed",
        "recipe_opened",
        "recipe_replaced",
        "recipe_completed",
        "recipe_added_to_shopping",
        "shopping_opened",
        "shopping_item_completed",
        "chat_opened",
        "chat_message_sent",
        "weight_added",
        "nutrition_log_added",
        "premium_screen_opened",
        "account_deleted",
        "data_export_requested",
        # Phase 19 daily loop
        "today_opened",
        "meal_completed",
        "meal_skipped",
        "food_added",
        "replacement_started",
        "replacement_completed",
        "replacement_failed",
        "water_added",
        "notification_enabled",
        "notification_disabled",
    }
)

FORBIDDEN_PROPERTY_KEYS = frozenset(
    {
        "email",
        "password",
        "token",
        "prompt",
        "profile",
        "restrictions",
        "weight",
        "api_key",
        "refresh_token",
        "access_token",
        "content",
        "message",
    }
)

MAX_PROPERTIES_BYTES = 2048
MAX_BATCH = 20


class AnalyticsValidationError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=422,
            code="analytics_validation_error",
            message=message,
        )


class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._session = session
        self._rate_limiter = rate_limiter

    async def ingest(
        self,
        *,
        user_id: UUID | None,
        events: list[dict[str, Any]],
        request_id: str | None,
        client_key: str,
    ) -> int:
        if not events:
            raise AnalyticsValidationError("Пустой batch.")
        if len(events) > MAX_BATCH:
            raise AnalyticsValidationError(f"Максимум {MAX_BATCH} событий за раз.")
        if self._rate_limiter is not None and user_id is not None:
            await self._rate_limiter.hit(
                f"analytics:{user_id}", limit=120, window_seconds=60
            )
        elif self._rate_limiter is not None:
            await self._rate_limiter.hit(
                f"analytics_ip:{client_key}", limit=60, window_seconds=60
            )

        accepted = 0
        now = utcnow()
        for raw in events:
            name = str(raw.get("event_name", ""))
            if name not in ALLOWED_EVENTS:
                raise AnalyticsValidationError(f"Неизвестное событие: {name}")
            props = raw.get("properties") or {}
            if not isinstance(props, dict):
                raise AnalyticsValidationError("properties должен быть объектом.")
            cleaned = self._sanitize_properties(props)
            blob = json.dumps(cleaned, ensure_ascii=False).encode("utf-8")
            if len(blob) > MAX_PROPERTIES_BYTES:
                raise AnalyticsValidationError("properties слишком большие.")
            # Prevent client spoofing of another user
            if "user_id" in props:
                raise AnalyticsValidationError("user_id в properties запрещён.")
            occurred = raw.get("occurred_at")
            occurred_at = now
            if isinstance(occurred, datetime):
                occurred_at = occurred
            elif isinstance(occurred, str) and occurred:
                try:
                    occurred_at = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
                except ValueError:
                    occurred_at = now
            row = ProductEvent(
                created_at=now,
                user_id=user_id,
                event_name=name,
                event_version=int(raw.get("event_version") or 1),
                occurred_at=occurred_at,
                platform=(str(raw["platform"])[:32] if raw.get("platform") else None),
                app_version=(
                    str(raw["app_version"])[:32] if raw.get("app_version") else None
                ),
                session_id=(str(raw["session_id"])[:64] if raw.get("session_id") else None),
                request_id=request_id,
                properties=cleaned,
            )
            self._session.add(row)
            accepted += 1
        await self._session.commit()
        return accepted

    @staticmethod
    def _sanitize_properties(props: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in props.items():
            lower = str(key).lower()
            if lower in FORBIDDEN_PROPERTY_KEYS or any(
                bad in lower for bad in ("password", "token", "secret", "prompt")
            ):
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                if isinstance(value, str) and len(value) > 128:
                    value = value[:128]
                cleaned[str(key)[:64]] = value
        return cleaned
