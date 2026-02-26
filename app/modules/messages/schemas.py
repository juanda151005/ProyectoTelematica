from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import MessageType


class MessageCreateRequest(BaseModel):
    content: Optional[str] = Field(default=None, max_length=5000)
    recipient_id: Optional[UUID] = None


class MessageReceiptOut(BaseModel):
    user_id: UUID
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_id: UUID
    group_id: UUID
    recipient_id: Optional[UUID]
    content: Optional[str]
    message_type: MessageType
    status: str
    created_at: datetime
    receipts: list[MessageReceiptOut] = Field(default_factory=list)
