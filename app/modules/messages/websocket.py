from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.group_connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, group_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.group_connections[group_id].add(websocket)

    def disconnect(self, group_id: UUID, websocket: WebSocket) -> None:
        self.group_connections[group_id].discard(websocket)
        if not self.group_connections[group_id]:
            self.group_connections.pop(group_id, None)

    async def broadcast(self, group_id: UUID, payload: dict) -> None:
        for connection in list(self.group_connections.get(group_id, set())):
            await connection.send_json(payload)


class UserNotificationManager:
    """Manages per-user WebSocket connections for cross-group notifications."""

    def __init__(self):
        self.user_connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        self.user_connections[user_id].discard(websocket)
        if not self.user_connections[user_id]:
            self.user_connections.pop(user_id, None)

    async def notify_user(self, user_id: UUID, payload: dict) -> None:
        for connection in list(self.user_connections.get(user_id, set())):
            try:
                await connection.send_json(payload)
            except Exception:
                self.user_connections[user_id].discard(connection)

    async def notify_users(self, user_ids: list[UUID], payload: dict) -> None:
        for user_id in user_ids:
            await self.notify_user(user_id, payload)


ws_manager = ConnectionManager()
user_notify_manager = UserNotificationManager()
