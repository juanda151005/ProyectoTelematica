from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.files.local_storage import LocalStorageAdapter
from app.modules.files.repository import FileRepository
from app.modules.files.schemas import FileUploadResponse
from app.modules.files.service import FilesService
from app.modules.groups.repository import GroupRepository
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import MessageOut
from app.modules.messages.service import MessagesService
from app.modules.messages.websocket import ws_manager
from app.modules.users.models import User
from app.shared.enums import MessageType
from app.shared.exceptions import PermissionDeniedError

router = APIRouter(prefix='/messages', tags=['files'])


@router.post('/file', response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    group_id: UUID = Form(...),
    recipient_id: Optional[UUID] = Form(default=None),
    content: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message_service = MessagesService(MessageRepository(db), GroupRepository(db))
    files_service = FilesService(LocalStorageAdapter(), FileRepository(db))

    try:
        message = message_service.send_message(
            sender_id=current_user.id,
            group_id=group_id,
            content=content or file.filename,
            recipient_id=recipient_id,
            message_type=MessageType.IMAGE if (file.content_type or '').startswith('image/') else MessageType.FILE,
        )

        file_bytes = await file.read()
        attachment = await files_service.upload_and_attach(
            message_id=message.id,
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type or 'application/octet-stream',
        )

        await ws_manager.broadcast(
            group_id,
            {
                'event': 'new_file',
                'data': MessageOut(
                    id=message.id,
                    sender_id=message.sender_id,
                    group_id=message.group_id,
                    recipient_id=message.recipient_id,
                    content=message.content,
                    message_type=message.message_type,
                    status=message.status,
                    created_at=message.created_at,
                    receipts=[],
                ).model_dump(mode='json'),
            },
        )

        return FileUploadResponse(message_id=message.id, file_id=attachment.id, file_url=attachment.url or '')
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
