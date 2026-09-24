"""EntitlementsService: tier resolution, require_premium, usage windows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.models import as_utc, utcnow
from app.entitlements import constants
from app.entitlements.errors import PremiumRequired, UsageLimitExceeded
from app.entitlements.models import Subscription, UsageLimit
from app.entitlements.provider import NullPaymentProvider, PaymentProvider
from app.entitlements.repository import EntitlementsRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UsageStatus:
    feature: str
    tier: str
    limit_value: int | None
    used_value: int
    remaining: int | None


class EntitlementsService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: EntitlementsRepository,
        settings: Settings,
        payment_provider: PaymentProvider | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._settings = settings
        self._payments = payment_provider or NullPaymentProvider()

    async def get_tier(self, user_id: UUID) -> str:
        subscription = await self._repository.get_active_subscription(user_id)
        if subscription is None:
            return constants.TIER_FREE
        if (
            subscription.current_period_end is not None
            and as_utc(subscription.current_period_end) < utcnow()
        ):
            return constants.TIER_FREE
        return subscription.tier

    async def ensure_free_subscription(self, user_id: UUID) -> Subscription:
        existing = await self._repository.get_active_subscription(user_id)
        if existing is not None:
            return existing
        row = Subscription(
            user_id=user_id,
            tier=constants.TIER_FREE,
            status=constants.STATUS_ACTIVE,
            provider=None,
            provider_subscription_id=None,
            current_period_start=utcnow(),
            current_period_end=None,
        )
        created = await self._repository.add_subscription(row)
        await self._session.commit()
        return created

    async def require_premium(self, user_id: UUID, feature: str) -> None:
        tier = await self.get_tier(user_id)
        if tier != constants.TIER_PREMIUM:
            raise PremiumRequired(feature)

    async def consume(
        self, user_id: UUID, feature: str, *, amount: int = 1
    ) -> UsageStatus:
        """Atomically check and increment a daily usage window before a paid call."""
        if feature in constants.PREMIUM_ONLY_FEATURES:
            await self.require_premium(user_id, feature)

        tier = await self.get_tier(user_id)
        limit = self._limit_for(tier, feature)
        if limit is None:
            return UsageStatus(
                feature=feature,
                tier=tier,
                limit_value=None,
                used_value=0,
                remaining=None,
            )

        window_start, window_end = self._utc_day_window()
        row = await self._repository.get_usage_window(user_id, feature, window_start)
        if row is None:
            row = await self._repository.add_usage(
                UsageLimit(
                    user_id=user_id,
                    feature=feature,
                    window_start=window_start,
                    window_end=window_end,
                    limit_value=limit,
                    used_value=0,
                )
            )

        if row.used_value + amount > row.limit_value:
            retry_after = max(
                1, int((as_utc(row.window_end) - utcnow()).total_seconds())
            )
            raise UsageLimitExceeded(feature, retry_after_seconds=retry_after)

        row.used_value += amount
        await self._session.flush()
        remaining = max(0, row.limit_value - row.used_value)
        return UsageStatus(
            feature=feature,
            tier=tier,
            limit_value=row.limit_value,
            used_value=row.used_value,
            remaining=remaining,
        )

    async def usage_status(self, user_id: UUID, feature: str) -> UsageStatus:
        tier = await self.get_tier(user_id)
        limit = self._limit_for(tier, feature)
        if limit is None:
            return UsageStatus(
                feature=feature,
                tier=tier,
                limit_value=None,
                used_value=0,
                remaining=None,
            )
        window_start, _ = self._utc_day_window()
        row = await self._repository.get_usage_window(user_id, feature, window_start)
        used = row.used_value if row is not None else 0
        return UsageStatus(
            feature=feature,
            tier=tier,
            limit_value=limit,
            used_value=used,
            remaining=max(0, limit - used),
        )

    def _limit_for(self, tier: str, feature: str) -> int | None:
        if tier == constants.TIER_PREMIUM:
            premium = self._settings.entitlement_premium_daily_limit
            return premium  # None = unlimited
        mapping = {
            constants.FEATURE_MEAL_PLAN_GENERATE: (
                self._settings.entitlement_free_meal_plan_per_day
            ),
            constants.FEATURE_MEAL_REPLACE: (
                self._settings.entitlement_free_meal_replace_per_day
            ),
            constants.FEATURE_CHAT_MESSAGE: (
                self._settings.entitlement_free_chat_per_day
            ),
            constants.FEATURE_AI_RECOMMENDATION: (
                self._settings.entitlement_free_ai_recommendation_per_day
            ),
            constants.FEATURE_IMAGE_REGENERATE: 0,
        }
        return mapping.get(feature, self._settings.entitlement_free_default_per_day)

    @staticmethod
    def _utc_day_window() -> tuple[datetime, datetime]:
        now = utcnow()
        start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        return start, start + timedelta(days=1)
