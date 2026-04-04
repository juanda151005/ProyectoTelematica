from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.groups.repository import GroupRepository
from app.modules.messages.repository import MessageRepository
from app.modules.messages.schemas import MessageCreateRequest, MessageOut, MessageReceiptOut, UnreadCountOut
from app.modules.messages.service import MessagesService
from app.modules.messages.websocket import ws_manager, user_notify_manager
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.enums import MessageType
from app.shared.exceptions import PermissionDeniedError

router = APIRouter(prefix='/groups', tags=['messages'])
unread_router = APIRouter(prefix='/messages', tags=['messages'])


def _to_message_out(message) -> MessageOut:
    file_url = None
    if getattr(message, 'attachments', None):
        file_url = message.attachments[0].url

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
        file_url=file_url,
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
        msg_json = out.model_dump(mode='json')

        # Broadcast to group WebSocket (existing behavior)
        await ws_manager.broadcast(group_id, {'event': 'new_message', 'data': msg_json})

        # Notify all group members via user notification WebSocket
        groups_repo = GroupRepository(db)
        member_ids = groups_repo.list_member_ids(group_id)
        sender_name = current_user.username if hasattr(current_user, 'username') else str(current_user.id)[:8]
        await user_notify_manager.notify_users(member_ids, {
            'event': 'new_message_notification',
            'data': {
                'group_id': str(group_id),
                'sender_id': str(current_user.id),
                'sender_name': sender_name,
                'content_preview': (payload.content or '')[:100],
                'message': msg_json,
            }
        })

        return out
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get('/{group_id}/messages', response_model=list[MessageOut])
async def get_messages(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mark_read: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MessagesService(MessageRepository(db), GroupRepository(db))
    try:
        messages, updated_ids = service.get_history(
            user_id=current_user.id,
            group_id=group_id,
            limit=limit,
            offset=offset,
            mark_read=mark_read,
        )
        out_messages = [_to_message_out(message) for message in messages]
        
        if updated_ids:
            updated_out = [msg for msg in out_messages if msg.id in updated_ids]
            await ws_manager.broadcast(group_id, {
                'event': 'receipts_updated',
                'data': {
                    'messages': [msg.model_dump(mode='json') for msg in updated_out]
                }
            })
            
        return out_messages
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@unread_router.get('/unread-counts', response_model=list[UnreadCountOut])
def get_unread_counts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns unread message counts per group for the authenticated user."""
    service = MessagesService(MessageRepository(db), GroupRepository(db))
    counts = service.get_unread_counts(current_user.id)
    return [UnreadCountOut(group_id=gid, count=cnt) for gid, cnt in counts.items()]
