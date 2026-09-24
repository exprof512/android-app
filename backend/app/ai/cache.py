"""Redis cache for successful Text AI structured responses."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Protocol


class TextAICacheStore(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ex: int) -> None: ...


class MemoryCacheStore:
    """Process-local store for unit tests — no Redis required."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        item = self._items.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, *, ex: int) -> None:
        expires_at = time.monotonic() + ex if ex > 0 else None
        self._items[key] = (value, expires_at)


class RedisCacheStore:
    """Adapter over redis.asyncio.Redis."""

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        if value is None:
            return None
        return value if isinstance(value, str) else value.decode()

    async def set(self, key: str, value: str, *, ex: int) -> None:
        await self._redis.set(key, value, ex=ex)


class TextAICache:
    def __init__(
        self, store: TextAICacheStore, *, ttl_seconds: int, schema_version: int
    ) -> None:
        self._store = store
        self._ttl = ttl_seconds
        self._schema_version = schema_version

    def fingerprint(self, *, operation: str, model: str, payload: dict[str, Any]) -> str:
        body: dict[str, Any] = {
            "operation": operation,
            "model": model,
            "schema_version": self._schema_version,
            "payload": payload,
        }
        for key in (
            "context_version",
            "prompt_version",
            "nutrition_policy_version",
        ):
            if key in payload and payload[key] is not None:
                body[key] = payload[key]
        canonical = json.dumps(
            body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _key(self, fingerprint: str) -> str:
        return f"ai:text:v{self._schema_version}:{fingerprint}"

    async def get(self, fingerprint: str) -> dict[str, Any] | None:
        raw = await self._store.get(self._key(fingerprint))
        if raw is None:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None

    async def set(self, fingerprint: str, value: dict[str, Any]) -> None:
        await self._store.set(
            self._key(fingerprint),
            json.dumps(value, ensure_ascii=False),
            ex=self._ttl,
        )
