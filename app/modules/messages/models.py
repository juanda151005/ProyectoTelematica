from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.shared.base_model import Base, TimestampMixin
from app.shared.enums import MessageType


class Message(Base, TimestampMixin):
    __tablename__ = 'messages'
    __table_args__ = (Index('ix_messages_group_created', 'group_id', 'created_at'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False, index=True)
    recipient_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType, native_enum=False), default=MessageType.TEXT, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='sent', nullable=False)

    sender = relationship('User', back_populates='sent_messages', foreign_keys=[sender_id])
    group = relationship('Group', back_populates='messages')
    receipts = relationship('MessageReceipt', back_populates='message', cascade='all, delete-orphan')
    attachments = relationship('FileAttachment', back_populates='message', cascade='all, delete-orphan')


class MessageReceipt(Base):
    __tablename__ = 'message_receipts'
    __table_args__ = (UniqueConstraint('message_id', 'user_id', name='uq_message_receipt'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    message = relationship('Message', back_populates='receipts')
