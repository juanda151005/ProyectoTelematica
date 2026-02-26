from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    async def save(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Retorna (path_local, url_publica)."""
