from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.groups.repository import GroupRepository
from app.modules.groups.service import GroupsService
from app.modules.messages.websocket import ws_manager
from app.modules.presence.repository import PresenceRepository
from app.modules.presence.service import PresenceService
from app.modules.users.repository import UserRepository
from app.shared.enums import UserStatus
from app.shared.exceptions import PermissionDeniedError

router = APIRouter(tags=['ws'])
settings = get_settings()


@router.websocket('/ws/groups/{group_id}')
async def group_ws(websocket: WebSocket, group_id: UUID, token: str = Query(default='')):
    db = SessionLocal()
    user = None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        sub = payload.get('sub')
        if not sub:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = UserRepository(db).get_by_id(UUID(sub))
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        GroupsService(GroupRepository(db), UserRepository(db)).ensure_membership(group_id, user.id)
        await ws_manager.connect(group_id, websocket)

        PresenceService(PresenceRepository(db)).set_online(user.id)
        user.status = UserStatus.ONLINE
        db.commit()

        while True:
            await websocket.receive_text()
    except (JWTError, PermissionDeniedError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    finally:
        if user:
            ws_manager.disconnect(group_id, websocket)
            PresenceService(PresenceRepository(db)).set_offline(user.id)
            user.status = UserStatus.OFFLINE
            db.commit()
        db.close()
