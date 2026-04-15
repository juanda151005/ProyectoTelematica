from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class GroupConnectionManager:
    def __init__(self):
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, group_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[group_id].add(ws)

    def disconnect(self, group_id: UUID, ws: WebSocket) -> None:
        self.connections[group_id].discard(ws)
        if not self.connections[group_id]:
            self.connections.pop(group_id, None)

    async def broadcast(self, group_id: UUID, payload: dict) -> None:
        for ws in list(self.connections.get(group_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.connections[group_id].discard(ws)


class UserConnectionManager:
    def __init__(self):
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[user_id].add(ws)

    def disconnect(self, user_id: UUID, ws: WebSocket) -> None:
        self.connections[user_id].discard(ws)
        if not self.connections[user_id]:
            self.connections.pop(user_id, None)

    async def notify(self, user_id: UUID, payload: dict) -> None:
        for ws in list(self.connections.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.connections[user_id].discard(ws)

    async def notify_many(self, user_ids: list[UUID], payload: dict) -> None:
        for uid in user_ids:
            await self.notify(uid, payload)


group_ws = GroupConnectionManager()
user_ws = UserConnectionManager()
