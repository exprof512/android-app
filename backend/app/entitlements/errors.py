"""Entitlement domain errors."""

from __future__ import annotations

from app.core.errors import ApiError


class PremiumRequired(ApiError):
    def __init__(self, feature: str) -> None:
        super().__init__(
            status_code=403,
            code="premium_required",
            message="Эта функция доступна в Premium.",
            details=[{"field": "feature", "reason": feature}],
        )


class UsageLimitExceeded(ApiError):
    def __init__(self, feature: str, *, retry_after_seconds: int | None = None) -> None:
        headers = (
            {"Retry-After": str(retry_after_seconds)}
            if retry_after_seconds is not None
            else None
        )
        super().__init__(
            status_code=429,
            code="usage_limit_exceeded",
            message="Достигнут лимит бесплатного тарифа на сегодня.",
            details=[{"field": "feature", "reason": feature}],
            headers=headers,
        )
