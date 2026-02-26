from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.shared.base_model import Base, TimestampMixin


class FileAttachment(Base, TimestampMixin):
    __tablename__ = 'file_attachments'

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    message = relationship('Message', back_populates='attachments')
