from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.presence.models import UserPresence


class PresenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id) -> Optional[UserPresence]:
        return self.db.get(UserPresence, user_id)

    def save(self, presence: UserPresence) -> UserPresence:
        self.db.add(presence)
        self.db.commit()
        self.db.refresh(presence)
        return presence
