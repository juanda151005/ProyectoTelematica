from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from app.config import get_settings


class StoragePort(ABC):
    @abstractmethod
    async def save(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        ...


class LocalStorageAdapter(StoragePort):
    def __init__(self):
        s = get_settings()
        self.base_path = Path(s.upload_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.public_base = s.public_url_base.rstrip("/")

    async def save(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        suffix = Path(filename).suffix
        stored = f"{uuid4()}{suffix}"
        path = self.base_path / stored
        path.write_bytes(file_bytes)
        return str(path), f"{self.public_base}/{stored}"


class S3StorageAdapter(StoragePort):
    def __init__(self):
        import boto3  # local import
        s = get_settings()
        self.bucket = s.s3_bucket
        self.region = s.s3_region
        self.client = boto3.client("s3", region_name=self.region)

    async def save(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        suffix = Path(filename).suffix
        stored = f"{uuid4()}{suffix}"
        self.client.put_object(Bucket=self.bucket, Key=stored, Body=file_bytes)
        url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{stored}"
        return stored, url


def get_storage() -> StoragePort:
    s = get_settings()
    return S3StorageAdapter() if s.storage_backend == "s3" else LocalStorageAdapter()
