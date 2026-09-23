"""Email delivery abstraction — no real SMTP vendor in Phase 17."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OutboundEmail:
    to_email: str
    subject: str
    body_text: str
    # Test-only; never logged in production paths.
    debug_token: str | None = None


class EmailProvider(Protocol):
    async def send(self, message: OutboundEmail) -> None: ...


@dataclass
class MockEmailProvider:
    """In-memory sink for development and automated tests."""

    sent: list[OutboundEmail] = field(default_factory=list)

    async def send(self, message: OutboundEmail) -> None:
        self.sent.append(message)

    def clear(self) -> None:
        self.sent.clear()

    def last_for(self, email: str) -> OutboundEmail | None:
        needle = email.strip().lower()
        for item in reversed(self.sent):
            if item.to_email.lower() == needle:
                return item
        return None
