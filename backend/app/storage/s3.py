"""S3-compatible storage (MinIO / AWS / R2 / Yandex)."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.storage.provider import StoredObject

logger = logging.getLogger(__name__)


class S3StorageProvider:
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
        public_base_url: str,
        use_ssl: bool = False,
        presigned_ttl_seconds: int = 300,
    ) -> None:
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")
        self._presigned_ttl = presigned_ttl_seconds
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            use_ssl=use_ssl,
            config=Config(signature_version="s3v4"),
        )

    async def ping(self) -> None:
        """Lightweight bucket reachability check for health endpoints."""

        def _head() -> None:
            self._client.head_bucket(Bucket=self._bucket)

        await asyncio.to_thread(_head)

    async def ensure_bucket(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(_ensure)

    async def upload(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        cache_control: str | None = None,
    ) -> StoredObject:
        extra: dict[str, Any] = {"ContentType": content_type}
        if cache_control:
            extra["CacheControl"] = cache_control

        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, **extra
            )

        await asyncio.to_thread(_put)
        return StoredObject(key=key, content_type=content_type, size=len(data))

    async def download(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        await asyncio.to_thread(_delete)

    def get_public_url(self, key: str) -> str:
        # FoodAI delivery URL — never the internal MinIO endpoint.
        relative = key.removeprefix("images/")
        return f"{self._public_base_url}/{relative}"

    async def get_presigned_url(self, key: str, *, expires_in: int | None = None) -> str:
        ttl = expires_in if expires_in is not None else self._presigned_ttl

        def _sign() -> str:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=ttl,
            )

        return await asyncio.to_thread(_sign)
