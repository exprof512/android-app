from __future__ import annotations

import pytest

from app.auth.passwords import PasswordHasher, UnsupportedPasswordHasher

PASSWORD = "correct horse battery staple"


def test_hash_is_argon2id_and_verifies() -> None:
    hasher = PasswordHasher()

    password_hash = hasher.hash(PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash
    assert hasher.verify(PASSWORD, password_hash) is True
    assert hasher.verify("wrong password", password_hash) is False


def test_each_hash_uses_a_fresh_salt() -> None:
    hasher = PasswordHasher()

    assert hasher.hash(PASSWORD) != hasher.hash(PASSWORD)


def test_malformed_hash_never_verifies() -> None:
    hasher = PasswordHasher()

    assert hasher.verify(PASSWORD, "not-a-hash") is False
    assert hasher.needs_rehash("not-a-hash") is True


def test_current_parameters_do_not_need_rehash() -> None:
    hasher = PasswordHasher()

    assert hasher.needs_rehash(hasher.hash(PASSWORD)) is False


def test_only_argon2id_is_accepted() -> None:
    with pytest.raises(UnsupportedPasswordHasher):
        PasswordHasher("bcrypt")
