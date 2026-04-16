"""Consume domain events and fan them out over WebSockets."""
from __future__ import annotations

import logging
import uuid

from app.clients import GroupsGRPCClient
from app.ws_manager import group_ws, user_ws

log = logging.getLogger(__name__)
_groups = GroupsGRPCClient()


async def handle_event(routing_key: str, payload: dict) -> None:
    try:
        if routing_key == "message.created":
            await _on_message_created(payload)
        elif routing_key == "message.read":
            await _on_message_read(payload)
        elif routing_key == "group.member.added":
            await _on_member_added(payload)
        elif routing_key == "group.member.removed":
            await _on_member_removed(payload)
    except Exception:  # noqa: BLE001
        log.exception("handler failed for %s", routing_key)


async def _on_message_created(payload: dict) -> None:
    gid_raw = payload.get("group_id")
    if not gid_raw:
        return
    group_id = uuid.UUID(gid_raw)
    await group_ws.broadcast(group_id, {"event": "new_message", "data": payload})

    # Push notification to all members
    member_ids = _groups.group_members(group_id)
    notif = {
        "event": "new_message_notification",
        "data": {
            "group_id": str(group_id),
            "sender_id": payload.get("sender_id"),
            "content_preview": (payload.get("content") or "")[:100],
            "message": payload,
        },
    }
    await user_ws.notify_many(member_ids, notif)


async def _on_message_read(payload: dict) -> None:
    gid_raw = payload.get("group_id")
    if not gid_raw:
        return
    await group_ws.broadcast(uuid.UUID(gid_raw), {"event": "receipts_updated", "data": {"messages": payload.get("messages", [])}})


async def _on_member_added(payload: dict) -> None:
    gid = payload.get("group_id")
    uid_raw = payload.get("user_id")
    if not (gid and uid_raw):
        return
    user_id = uuid.UUID(uid_raw)
    # 1) tell the group channel
    await group_ws.broadcast(uuid.UUID(gid), {"event": "member_added", "data": payload})
    # 2) tell the user their sidebar has a new group
    await user_ws.notify(user_id, {
        "event": "added_to_group",
        "data": {
            "id": gid,
            "name": payload.get("group_name") or "Grupo",
            "admin_id": payload.get("added_by"),
            "settings": {"is_dm": bool(payload.get("is_dm"))},
        },
    })


async def _on_member_removed(payload: dict) -> None:
    gid = payload.get("group_id")
    if not gid:
        return
    await group_ws.broadcast(uuid.UUID(gid), {"event": "member_removed", "data": payload})
