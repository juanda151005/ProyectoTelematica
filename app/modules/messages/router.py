from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.groups.repository import GroupRepository
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import MessageCreateRequest, MessageOut, MessageReceiptOut
from app.modules.messages.service import MessagesService
from app.modules.messages.websocket import ws_manager
from app.modules.users.models import User
from app.shared.enums import MessageType
from app.shared.exceptions import PermissionDeniedError

router = APIRouter(prefix='/groups', tags=['messages'])


def _to_message_out(message) -> MessageOut:
    return MessageOut(
        id=message.id,
        sender_id=message.sender_id,
        group_id=message.group_id,
        recipient_id=message.recipient_id,
        content=message.content,
        message_type=message.message_type,
        status=message.status,
        created_at=message.created_at,
        receipts=[
            MessageReceiptOut(user_id=r.user_id, delivered_at=r.delivered_at, read_at=r.read_at)
            for r in message.receipts
        ],
    )


@router.post('/{group_id}/messages', response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    group_id: UUID,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MessagesService(MessageRepository(db), GroupRepository(db))
    try:
        message = service.send_message(
            sender_id=current_user.id,
            group_id=group_id,
            content=payload.content,
            recipient_id=payload.recipient_id,
            message_type=MessageType.TEXT,
        )
        out = _to_message_out(message)
        await ws_manager.broadcast(group_id, {'event': 'new_message', 'data': out.model_dump(mode='json')})
        return out
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get('/{group_id}/messages', response_model=list[MessageOut])
def get_messages(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mark_read: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MessagesService(MessageRepository(db), GroupRepository(db))
    try:
        messages = service.get_history(
            user_id=current_user.id,
            group_id=group_id,
            limit=limit,
            offset=offset,
            mark_read=mark_read,
        )
        return [_to_message_out(message) for message in messages]
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
