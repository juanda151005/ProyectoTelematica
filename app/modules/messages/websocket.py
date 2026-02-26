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


ws_manager = ConnectionManager()
