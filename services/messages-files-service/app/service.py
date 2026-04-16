from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from app.clients import GroupsGRPCClient
from app.models import FileAttachment, Message, MessageReceipt
from app.repository import FileRepository, MessageRepository
from app.storage import StoragePort


class PermissionDeniedError(Exception):
    pass


class MessagesService:
    def __init__(self, repo: MessageRepository, groups: GroupsGRPCClient):
        self.repo = repo
        self.groups = groups

    def _ensure_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not self.groups.is_member(group_id, user_id):
            raise PermissionDeniedError("No perteneces a este grupo")

    def send(self, sender_id: uuid.UUID, group_id: uuid.UUID, content: Optional[str], recipient_id: Optional[uuid.UUID], message_type: str = "text") -> Message:
        self._ensure_member(group_id, sender_id)
        if recipient_id is not None:
            self._ensure_member(group_id, recipient_id)

        msg = Message(
            sender_id=sender_id,
            group_id=group_id,
            recipient_id=recipient_id,
            content=content,
            message_type=message_type,
            status="sent",
        )
        msg = self.repo.create(msg)

        member_ids = self.groups.group_members(group_id)
        receipts = []
        now = self.repo.utcnow()
        for mid in member_ids:
            if recipient_id and mid != recipient_id and mid != sender_id:
                continue
            r = MessageReceipt(message_id=msg.id, user_id=mid)
            if mid == sender_id:
                r.delivered_at = now
                r.read_at = now
            receipts.append(r)
        self.repo.create_receipts(receipts)
        return self.repo.get(msg.id)

    def history(self, user_id: uuid.UUID, group_id: uuid.UUID, limit: int, offset: int, mark_read: bool):
        self._ensure_member(group_id, user_id)
        msgs = self.repo.list_group(group_id, limit=limit, offset=offset)
        ids = [m.id for m in msgs]
        if not ids:
            return msgs, []
        receipts = self.repo.receipts_for_user(user_id, ids)
        now = self.repo.utcnow()
        updated = set()
        changed = False
        for r in receipts:
            if r.delivered_at is None:
                r.delivered_at = now
                updated.add(r.message_id)
                changed = True
            if mark_read and r.read_at is None:
                r.read_at = now
                updated.add(r.message_id)
                changed = True
        if changed:
            self.repo.save()
        return self.repo.list_group(group_id, limit=limit, offset=offset), list(updated)

    def unread_counts(self, user_id: uuid.UUID) -> dict:
        return self.repo.unread_per_group(user_id)


class FilesService:
    def __init__(self, storage: StoragePort, repo: FileRepository):
        self.storage = storage
        self.repo = repo

    async def attach(self, message_id: uuid.UUID, file_bytes: bytes, filename: str, content_type: str) -> FileAttachment:
        path, url = await self.storage.save(file_bytes, filename)
        att = FileAttachment(
            message_id=message_id,
            original_name=filename,
            stored_name=Path(path).name,
            content_type=content_type,
            size_bytes=len(file_bytes),
            path=path,
            url=url,
        )
        return self.repo.create(att)
