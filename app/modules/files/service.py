from pathlib import Path

from app.modules.files.models import FileAttachment
from app.modules.files.repository import FileRepository
from app.modules.files.storage_port import StoragePort


class FilesService:
    def __init__(self, storage: StoragePort, repo: FileRepository):
        self.storage = storage
        self.repo = repo

    async def upload_and_attach(self, message_id, file_bytes: bytes, filename: str, content_type: str) -> FileAttachment:
        saved_path, public_url = await self.storage.save(file_bytes, filename)
        attachment = FileAttachment(
            message_id=message_id,
            original_name=filename,
            stored_name=Path(saved_path).name,
            content_type=content_type,
            size_bytes=len(file_bytes),
            path=saved_path,
            url=public_url,
        )
        return self.repo.create(attachment)
