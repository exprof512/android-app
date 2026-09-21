from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.auth.models import User
from app.auth.ownership import ensure_owner, ensure_owns
from app.core.errors import OwnershipDenied


@dataclass
class OwnedRow:
    user_id: UUID


def build_user() -> User:
    return User(id=uuid4(), email="anna@example.com", password_hash="hash")


def test_owner_passes_the_guard() -> None:
    user = build_user()

    ensure_owner(user, user.id)
    ensure_owns(user, OwnedRow(user_id=user.id))


def test_other_users_resource_is_denied() -> None:
    user = build_user()

    with pytest.raises(OwnershipDenied) as denied:
        ensure_owner(user, uuid4())

    assert denied.value.status_code == 403
    assert denied.value.code == "ownership_denied"


def test_other_users_row_is_denied() -> None:
    user = build_user()

    with pytest.raises(OwnershipDenied):
        ensure_owns(user, OwnedRow(user_id=uuid4()))
