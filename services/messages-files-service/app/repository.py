from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import FileAttachment, Message, MessageReceipt


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, message: Message) -> Message:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def create_receipts(self, receipts: list[MessageReceipt]) -> None:
        self.db.add_all(receipts)
        self.db.commit()

    def get(self, message_id: uuid.UUID):
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(joinedload(Message.receipts), joinedload(Message.attachments))
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_group(self, group_id: uuid.UUID, limit: int = 50, offset: int = 0):
        stmt = (
            select(Message)
            .where(Message.group_id == group_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(joinedload(Message.receipts), joinedload(Message.attachments))
        )
        return list(reversed(self.db.execute(stmt).unique().scalars().all()))

    def receipts_for_user(self, user_id: uuid.UUID, message_ids: list[uuid.UUID]):
        if not message_ids:
            return []
        stmt = select(MessageReceipt).where(
            MessageReceipt.user_id == user_id,
            MessageReceipt.message_id.in_(message_ids),
        )
        return list(self.db.execute(stmt).scalars().all())

    def unread_per_group(self, user_id: uuid.UUID) -> dict:
        stmt = (
            select(Message.group_id, func.count(MessageReceipt.id))
            .join(MessageReceipt, MessageReceipt.message_id == Message.id)
            .where(MessageReceipt.user_id == user_id, MessageReceipt.read_at.is_(None))
            .group_by(Message.group_id)
        )
        return {row[0]: row[1] for row in self.db.execute(stmt).all()}

    def save(self) -> None:
        self.db.commit()

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, att: FileAttachment) -> FileAttachment:
        self.db.add(att)
        self.db.commit()
        self.db.refresh(att)
        return att
