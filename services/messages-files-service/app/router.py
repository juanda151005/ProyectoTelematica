from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.clients import GroupsGRPCClient
from app.config import get_settings
from app.database import get_db
from app.repository import FileRepository, MessageRepository
from app.schemas import FileUploadResponse, MessageCreateRequest, MessageOut, MessageReceiptOut, UnreadCountOut
from app.service import FilesService, MessagesService, PermissionDeniedError
from app.storage import get_storage
from groupsapp_shared.security import decode_user_id

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def current_user_id(token: str | None = Depends(oauth2_scheme)) -> uuid.UUID:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    uid = decode_user_id(token, settings.secret_key, settings.algorithm)
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    return uid


def svc(db: Session = Depends(get_db)) -> MessagesService:
    return MessagesService(MessageRepository(db), GroupsGRPCClient())


def _to_out(message) -> MessageOut:
    file_url = message.attachments[0].url if message.attachments else None
    return MessageOut(
        id=message.id,
        sender_id=message.sender_id,
        group_id=message.group_id,
        recipient_id=message.recipient_id,
        content=message.content,
        message_type=message.message_type,
        status=message.status,
        created_at=message.created_at,
        receipts=[MessageReceiptOut(user_id=r.user_id, delivered_at=r.delivered_at, read_at=r.read_at) for r in message.receipts],
        file_url=file_url,
    )


groups_router = APIRouter(prefix="/api/v1/groups", tags=["messages"])
messages_router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@groups_router.post("/{group_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(group_id: uuid.UUID, payload: MessageCreateRequest, uid: uuid.UUID = Depends(current_user_id), s: MessagesService = Depends(svc)):
    from app.main import bus, publish_message_created
    try:
        msg = s.send(uid, group_id, payload.content, payload.recipient_id, message_type="text")
        out = _to_out(msg)
        await publish_message_created(out)
        return out
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))


@groups_router.get("/{group_id}/messages", response_model=list[MessageOut])
async def list_messages(
    group_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mark_read: bool = Query(True),
    uid: uuid.UUID = Depends(current_user_id),
    s: MessagesService = Depends(svc),
):
    from app.main import publish_receipts_updated
    try:
        msgs, updated = s.history(uid, group_id, limit, offset, mark_read)
        out = [_to_out(m) for m in msgs]
        if updated:
            await publish_receipts_updated(group_id, [o for o in out if o.id in updated])
        return out
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))


@messages_router.get("/unread-counts", response_model=list[UnreadCountOut])
def unread(uid: uuid.UUID = Depends(current_user_id), db: Session = Depends(get_db)):
    counts = MessagesService(MessageRepository(db), GroupsGRPCClient()).unread_counts(uid)
    return [UnreadCountOut(group_id=gid, count=c) for gid, c in counts.items()]


@messages_router.post("/file", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    group_id: uuid.UUID = Form(...),
    recipient_id: Optional[uuid.UUID] = Form(default=None),
    content: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    uid: uuid.UUID = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    from app.main import publish_message_created
    msgs = MessagesService(MessageRepository(db), GroupsGRPCClient())
    files = FilesService(get_storage(), FileRepository(db))

    try:
        mtype = "image" if (file.content_type or "").startswith("image/") else "file"
        msg = msgs.send(uid, group_id, content or file.filename, recipient_id, message_type=mtype)
        data = await file.read()
        att = await files.attach(msg.id, data, file.filename or "file", file.content_type or "application/octet-stream")
        msg = MessageRepository(db).get(msg.id)  # reload with attachment
        out = _to_out(msg)
        await publish_message_created(out)
        return FileUploadResponse(message_id=msg.id, file_id=att.id, file_url=att.url or "")
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))
