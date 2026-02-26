from __future__ import annotations

from typing import Optional

from app.modules.groups.repository import GroupRepository
from app.modules.messages.models import Message, MessageReceipt
from app.modules.messages.repository import MessageRepository
from app.shared.enums import MessageType
from app.shared.exceptions import PermissionDeniedError


class MessagesService:
    def __init__(self, messages_repo: MessageRepository, groups_repo: GroupRepository):
        self.messages_repo = messages_repo
        self.groups_repo = groups_repo

    def _ensure_membership(self, group_id, user_id) -> None:
        membership = self.groups_repo.get_member(group_id, user_id)
        if not membership:
            raise PermissionDeniedError('No perteneces a este grupo')

    def send_message(
        self,
        sender_id,
        group_id,
        content: Optional[str],
        recipient_id=None,
        message_type: MessageType = MessageType.TEXT,
    ):
        self._ensure_membership(group_id, sender_id)
        if recipient_id is not None:
            self._ensure_membership(group_id, recipient_id)

        message = Message(
            sender_id=sender_id,
            group_id=group_id,
            recipient_id=recipient_id,
            content=content,
            message_type=message_type,
            status='sent',
        )
        message = self.messages_repo.create_message(message)

        member_ids = self.groups_repo.list_member_ids(group_id)
        receipts = []
        now = self.messages_repo.utcnow()
        for member_id in member_ids:
            if recipient_id and member_id != recipient_id and member_id != sender_id:
                continue
            receipt = MessageReceipt(message_id=message.id, user_id=member_id)
            if member_id == sender_id:
                receipt.delivered_at = now
                receipt.read_at = now
            receipts.append(receipt)

        self.messages_repo.create_receipts(receipts)
        return self.messages_repo.get_message(message.id)

    def get_history(self, user_id, group_id, limit: int, offset: int, mark_read: bool = True):
        self._ensure_membership(group_id, user_id)
        messages = self.messages_repo.list_group_messages(group_id, limit=limit, offset=offset)
        message_ids = [msg.id for msg in messages]

        if not message_ids:
            return messages

        receipts = self.messages_repo.list_receipts_for_user(user_id, message_ids)
        now = self.messages_repo.utcnow()
        changed = False

        for receipt in receipts:
            if receipt.delivered_at is None:
                receipt.delivered_at = now
                changed = True
            if mark_read and receipt.read_at is None:
                receipt.read_at = now
                changed = True

        if changed:
            self.messages_repo.save()

        return self.messages_repo.list_group_messages(group_id, limit=limit, offset=offset)
