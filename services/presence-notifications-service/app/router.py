from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clients import GroupsGRPCClient
from app.config import get_settings
from app.database import get_db
from app.service import PresenceService
from app.ws_manager import group_ws, user_ws
from groupsapp_shared.security import decode_user_id

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def current_user_id(token: str | None = Depends(oauth2_scheme)) -> uuid.UUID:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    uid = decode_user_id(token, settings.secret_key, settings.algorithm)
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    return uid


class PresenceOut(BaseModel):
    user_id: uuid.UUID
    is_online: bool
    last_seen: Optional[datetime]


users_router = APIRouter(prefix="/api/v1/users", tags=["presence"])
presence_router = APIRouter(prefix="/api/v1/presence", tags=["presence"])
ws_router = APIRouter(tags=["ws"])


@users_router.get("/{user_id}/presence", response_model=PresenceOut)
def get_presence(user_id: uuid.UUID, db: Session = Depends(get_db), _=Depends(current_user_id)):
    p = PresenceService(db).get(user_id)
    return PresenceOut(user_id=p.user_id, is_online=p.is_online, last_seen=p.last_seen)


@presence_router.get("/{user_id}", response_model=PresenceOut)
def get_presence_alt(user_id: uuid.UUID, db: Session = Depends(get_db), _=Depends(current_user_id)):
    p = PresenceService(db).get(user_id)
    return PresenceOut(user_id=p.user_id, is_online=p.is_online, last_seen=p.last_seen)


async def _publish_presence_change(user_id: uuid.UUID, is_online: bool) -> None:
    from app.main import bus
    from groupsapp_shared.events import EventKeys
    await bus.publish(EventKeys.PRESENCE_CHANGED, {"user_id": str(user_id), "is_online": is_online})


@ws_router.websocket("/ws/groups/{group_id}")
async def group_websocket(websocket: WebSocket, group_id: uuid.UUID, token: str = Query(default="")):
    from app.database import SessionLocal
    uid = decode_user_id(token, settings.secret_key, settings.algorithm)
    if not uid:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not GroupsGRPCClient().is_member(group_id, uid):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    try:
        await group_ws.connect(group_id, websocket)
        PresenceService(db).set_online(uid)
        await _publish_presence_change(uid, True)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        group_ws.disconnect(group_id, websocket)
        PresenceService(db).set_offline(uid)
        await _publish_presence_change(uid, False)
        db.close()


@ws_router.websocket("/ws/notifications")
async def notifications_websocket(websocket: WebSocket, token: str = Query(default="")):
    from app.database import SessionLocal
    uid = decode_user_id(token, settings.secret_key, settings.algorithm)
    if not uid:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db = SessionLocal()
    try:
        await user_ws.connect(uid, websocket)
        PresenceService(db).set_online(uid)
        await _publish_presence_change(uid, True)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        user_ws.disconnect(uid, websocket)
        PresenceService(db).set_offline(uid)
        await _publish_presence_change(uid, False)
        db.close()
