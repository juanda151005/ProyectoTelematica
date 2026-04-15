from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import UserPresence


class PresenceService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create(self, user_id: uuid.UUID) -> UserPresence:
        p = self.db.get(UserPresence, user_id)
        if p:
            return p
        p = UserPresence(user_id=user_id, is_online=False)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def set_online(self, user_id: uuid.UUID) -> UserPresence:
        p = self._get_or_create(user_id)
        p.is_online = True
        self.db.commit()
        return p

    def set_offline(self, user_id: uuid.UUID) -> UserPresence:
        p = self._get_or_create(user_id)
        p.is_online = False
        p.last_seen = utcnow()
        self.db.commit()
        return p

    def get(self, user_id: uuid.UUID) -> UserPresence:
        return self._get_or_create(user_id)
