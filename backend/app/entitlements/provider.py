"""PaymentProvider interface — no real billing adapter in MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class EntitlementSnapshot:
    tier: str
    status: str
    provider: str | None = None


class PaymentProvider(Protocol):
    """Future adapters: Google Play, RU provider, international provider."""

    async def create_purchase(self, user_id: UUID, product_id: str) -> str: ...

    async def verify_purchase(self, user_id: UUID, receipt: str) -> EntitlementSnapshot: ...

    async def cancel(self, user_id: UUID, subscription_id: str) -> None: ...

    async def get_entitlement(self, user_id: UUID) -> EntitlementSnapshot | None: ...


class NullPaymentProvider:
    """Placeholder used until a real provider is wired."""

    async def create_purchase(self, user_id: UUID, product_id: str) -> str:
        raise NotImplementedError("payment_provider_not_configured")

    async def verify_purchase(self, user_id: UUID, receipt: str) -> EntitlementSnapshot:
        raise NotImplementedError("payment_provider_not_configured")

    async def cancel(self, user_id: UUID, subscription_id: str) -> None:
        raise NotImplementedError("payment_provider_not_configured")

    async def get_entitlement(self, user_id: UUID) -> EntitlementSnapshot | None:
        return None
