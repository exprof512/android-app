"""Object storage abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_type: str
    size: int


class StorageProvider(Protocol):
    async def upload(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        cache_control: str | None = None,
    ) -> StoredObject: ...

    async def download(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    def get_public_url(self, key: str) -> str: ...

    async def get_presigned_url(self, key: str, *, expires_in: int) -> str: ...
