from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.modules.files.storage_port import StoragePort


class LocalStorageAdapter(StoragePort):
    def __init__(self):
        settings = get_settings()
        self.base_path = Path(settings.upload_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        suffix = Path(filename).suffix
        stored_name = f'{uuid4()}{suffix}'
        full_path = self.base_path / stored_name
        full_path.write_bytes(file_bytes)
        public_url = f'/uploads/{stored_name}'
        return str(full_path), public_url
