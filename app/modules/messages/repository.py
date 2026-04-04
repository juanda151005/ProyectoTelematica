from datetime import datetime, timezone

from sqlalchemy import func, select
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

    def count_unread_per_group(self, user_id) -> dict:
        """Returns {group_id: unread_count} for all groups the user has unread messages in."""
        stmt = (
            select(Message.group_id, func.count(MessageReceipt.id))
            .join(MessageReceipt, MessageReceipt.message_id == Message.id)
            .where(
                MessageReceipt.user_id == user_id,
                MessageReceipt.read_at.is_(None),
            )
            .group_by(Message.group_id)
        )
        rows = self.db.execute(stmt).all()
        return {row[0]: row[1] for row in rows}

    def save(self) -> None:
        self.db.commit()

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
