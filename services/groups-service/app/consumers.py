"""Event consumers: keep local state consistent with other services."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.database import SessionLocal
from app.repository import GroupRepository

log = logging.getLogger(__name__)


async def handle_event(routing_key: str, payload: dict) -> None:
    if routing_key == "message.created":
        await _on_message_created(payload)


async def _on_message_created(payload: dict) -> None:
    gid = payload.get("group_id")
    if not gid:
        return
    ts_raw = payload.get("created_at")
    ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else datetime.utcnow()
    db = SessionLocal()
    try:
        GroupRepository(db).touch_last_message(uuid.UUID(gid), ts)
    finally:
        db.close()
