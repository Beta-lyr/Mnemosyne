"""Unified storage abstraction — local filesystem or S3-compatible object storage.

Usage:
    from mnemosyne.storage import storage
    url = await storage.save(b"image bytes", "characters/{id}/images", "gen_abc.png")
    data = await storage.read("characters/{id}/images/gen_abc.png")
"""

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, key: str) -> str:
        """Save data and return the URL path for retrieval."""
        ...

    @abstractmethod
    async def read(self, key: str) -> bytes | None:
        """Read data by key. Returns None if not found."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a file. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = base_dir

    async def save(self, data: bytes, key: str) -> str:
        path = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        logger.info("Local save: %s (%d bytes)", path, len(data))
        return f"/uploads/{key}"

    async def read(self, key: str) -> bytes | None:
        path = os.path.join(self.base_dir, key)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        path = os.path.join(self.base_dir, key)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return os.path.isfile(os.path.join(self.base_dir, key))


class S3Storage(StorageBackend):
    def __init__(self, bucket: str, endpoint_url: str, access_key: str, secret_key: str, prefix: str = "mnemosyne/uploads"):
        import boto3
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}"

    async def save(self, data: bytes, key: str) -> str:
        full_key = self._full_key(key)
        self.client.put_object(Bucket=self.bucket, Key=full_key, Body=data)
        logger.info("S3 save: s3://%s/%s (%d bytes)", self.bucket, full_key, len(data))
        return f"/api/storage/{key}"

    async def read(self, key: str) -> bytes | None:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=self._full_key(key))
            return resp["Body"].read()
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except Exception:
            return False


def _create_storage() -> StorageBackend:
    from mnemosyne.config import settings
    if settings.s3_bucket and settings.s3_endpoint_url and settings.s3_access_key:
        try:
            s3 = S3Storage(
                bucket=settings.s3_bucket,
                endpoint_url=settings.s3_endpoint_url,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                prefix=settings.s3_prefix,
            )
            # Quick connectivity check — list bucket (cheap HEAD request)
            s3.client.head_bucket(Bucket=settings.s3_bucket)
            logger.info("S3 storage connected: bucket=%s endpoint=%s", settings.s3_bucket, settings.s3_endpoint_url)
            return s3
        except Exception as e:
            logger.warning("S3 connection failed (%s), falling back to local storage", e)
    return LocalStorage()


storage: StorageBackend = _create_storage()
