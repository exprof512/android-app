"""In-memory StorageProvider for unit tests."""

from __future__ import annotations

from app.storage.provider import StoredObject


class MemoryStorageProvider:
    def __init__(self, *, public_base_url: str = "http://testserver/media") -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}
        self._public_base_url = public_base_url.rstrip("/")

    async def ping(self) -> None:
        return None

    async def upload(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        cache_control: str | None = None,
    ) -> StoredObject:
        self._objects[key] = (data, content_type)
        return StoredObject(key=key, content_type=content_type, size=len(data))

    async def download(self, key: str) -> bytes:
        if key not in self._objects:
            raise FileNotFoundError(key)
        return self._objects[key][0]

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    def get_public_url(self, key: str) -> str:
        relative = key.removeprefix("images/")
        return f"{self._public_base_url}/{relative}"

    async def get_presigned_url(self, key: str, *, expires_in: int) -> str:
        return self.get_public_url(key)
