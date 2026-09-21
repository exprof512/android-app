"""Argon2id password hashing."""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError
from argon2.low_level import Type

SUPPORTED_ALGORITHM = "argon2id"

_TIME_COST = 3
_MEMORY_COST_KIB = 65536
_PARALLELISM = 4
_HASH_LEN = 32
_SALT_LEN = 16

_TIMING_EQUALIZER_PASSWORD = "foodai-timing-equalizer"


class UnsupportedPasswordHasher(RuntimeError):
    """Raised when configuration asks for an algorithm the backend does not allow."""


class PasswordHasher:
    """Wraps argon2-cffi so the rest of the code never sees provider exceptions."""

    def __init__(self, algorithm: str = SUPPORTED_ALGORITHM) -> None:
        if algorithm != SUPPORTED_ALGORITHM:
            raise UnsupportedPasswordHasher(
                f"PASSWORD_HASHER must be {SUPPORTED_ALGORITHM}."
            )
        self._hasher = Argon2PasswordHasher(
            time_cost=_TIME_COST,
            memory_cost=_MEMORY_COST_KIB,
            parallelism=_PARALLELISM,
            hash_len=_HASH_LEN,
            salt_len=_SALT_LEN,
            type=Type.ID,
        )
        self._equalizer_hash: str | None = None

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (Argon2Error, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except (Argon2Error, InvalidHashError):
            return True

    def spend_verification_time(self) -> None:
        """Verify a throwaway hash so unknown emails cost the same as known ones."""
        if self._equalizer_hash is None:
            self._equalizer_hash = self.hash(_TIMING_EQUALIZER_PASSWORD)
        self.verify("wrong-password", self._equalizer_hash)
