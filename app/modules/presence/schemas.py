from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PresenceOut(BaseModel):
    user_id: UUID
    is_online: bool
    last_seen: Optional[datetime]
