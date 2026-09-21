"""Ownership guard applied before reading or mutating a user-owned resource."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.auth.models import User
from app.core.errors import OwnershipDenied


class OwnedResource(Protocol):
    """Any row that stores the owning ``user_id``."""

    user_id: UUID


def ensure_owner(user: User, owner_id: UUID) -> None:
    if owner_id != user.id:
        raise OwnershipDenied()


def ensure_owns(user: User, resource: OwnedResource) -> None:
    ensure_owner(user, resource.user_id)
