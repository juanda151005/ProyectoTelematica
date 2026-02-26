from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.shared.base_model import Base


class UserPresence(Base):
    __tablename__ = 'user_presence'

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    is_online: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='presence')

    def mark_online(self) -> None:
        self.is_online = True

    def mark_offline(self) -> None:
        self.is_online = False
        self.last_seen = datetime.now(timezone.utc)
