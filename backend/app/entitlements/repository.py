"""Persistence for subscriptions and usage windows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entitlements.constants import STATUS_ACTIVE
from app.entitlements.models import Subscription, UsageLimit


class EntitlementsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_subscription(self, user_id: UUID) -> Subscription | None:
        statement = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == STATUS_ACTIVE,
            )
            .order_by(Subscription.current_period_start.desc())
            .limit(1)
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def add_subscription(self, subscription: Subscription) -> Subscription:
        self._session.add(subscription)
        await self._session.flush()
        return subscription

    async def get_usage_window(
        self, user_id: UUID, feature: str, window_start: datetime
    ) -> UsageLimit | None:
        statement = select(UsageLimit).where(
            UsageLimit.user_id == user_id,
            UsageLimit.feature == feature,
            UsageLimit.window_start == window_start,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def add_usage(self, row: UsageLimit) -> UsageLimit:
        self._session.add(row)
        await self._session.flush()
        return row
