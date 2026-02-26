from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.enums import UserStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    status: UserStatus


class PresenceOut(BaseModel):
    user_id: UUID
    is_online: bool
    last_seen: Optional[datetime]
