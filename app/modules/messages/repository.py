from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.messages.models import Message, MessageReceipt


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_message(self, message: Message) -> Message:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def create_receipts(self, receipts: list[MessageReceipt]) -> None:
        self.db.add_all(receipts)
        self.db.commit()

    def get_message(self, message_id):
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(joinedload(Message.receipts), joinedload(Message.attachments))
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_group_messages(self, group_id, limit: int = 50, offset: int = 0):
        stmt = (
            select(Message)
            .where(Message.group_id == group_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(joinedload(Message.receipts), joinedload(Message.attachments))
        )
        return list(reversed(self.db.execute(stmt).unique().scalars().all()))

    def list_receipts_for_user(self, user_id, message_ids: list):
        stmt = select(MessageReceipt).where(MessageReceipt.user_id == user_id, MessageReceipt.message_id.in_(message_ids))
        return list(self.db.execute(stmt).scalars().all())

    def save(self) -> None:
        self.db.commit()

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
