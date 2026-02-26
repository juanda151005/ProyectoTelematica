from uuid import UUID

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    message_id: UUID
    file_id: UUID
    file_url: str
