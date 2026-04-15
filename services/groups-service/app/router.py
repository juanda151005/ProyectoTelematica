from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.clients import UsersGRPCClient
from app.config import get_settings
from app.database import get_db
from app.repository import GroupRepository
from app.schemas import (
    AddMemberRequest,
    CreateDMRequest,
    GroupCreateRequest,
    GroupMemberDetailOut,
    GroupMemberOut,
    GroupOut,
    UpdateRoleRequest,
)
from app.service import ConflictError, GroupsService, NotFoundError, PermissionDeniedError
from groupsapp_shared.events import EventBus, EventKeys
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


def svc(db: Session = Depends(get_db)) -> GroupsService:
    return GroupsService(GroupRepository(db), UsersGRPCClient())


router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


def _map_errors(fn):
    # Decorator-like helper for route handlers (inline try/except style).
    raise NotImplementedError


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(payload: GroupCreateRequest, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    from app.main import bus
    group = s.create_group(payload.name, uid, payload.settings)
    await bus.publish(EventKeys.GROUP_CREATED, {"group_id": str(group.id), "name": group.name, "admin_id": str(uid), "settings": group.settings})
    return group


@router.get("", response_model=list[GroupOut])
def list_my_groups(uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    return s.list_user_groups(uid)


@router.post("/dm", response_model=GroupOut, status_code=201)
async def create_dm(payload: CreateDMRequest, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    from app.main import bus
    try:
        group = s.get_or_create_dm(uid, payload.user_id)
        await bus.publish(EventKeys.GROUP_MEMBER_ADDED, {
            "group_id": str(group.id),
            "user_id": str(payload.user_id),
            "added_by": str(uid),
            "group_name": group.name,
            "is_dm": True,
        })
        return group
    except NotFoundError as e:
        raise HTTPException(404, str(e))
    except ConflictError as e:
        raise HTTPException(409, str(e))


@router.post("/{group_id}/members", response_model=GroupMemberOut, status_code=201)
async def add_member(group_id: uuid.UUID, payload: AddMemberRequest, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    from app.main import bus
    if not payload.username:
        raise HTTPException(422, "username required")
    try:
        member, user = s.add_member_by_username(group_id, uid, payload.username)
        await bus.publish(EventKeys.GROUP_MEMBER_ADDED, {
            "group_id": str(group_id),
            "user_id": user["id"],
            "username": user["username"],
            "added_by": str(uid),
            "role": member.role,
            "is_dm": False,
        })
        return GroupMemberOut(group_id=member.group_id, user_id=member.user_id, role=member.role)
    except NotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))
    except ConflictError as e:
        raise HTTPException(409, str(e))


@router.get("/{group_id}/members", response_model=list[GroupMemberDetailOut])
def members(group_id: uuid.UUID, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    try:
        return s.members_detail(group_id, uid)
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(group_id: uuid.UUID, user_id: uuid.UUID, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    from app.main import bus
    try:
        s.remove_member(group_id, uid, user_id)
        await bus.publish("group.member.removed", {"group_id": str(group_id), "user_id": str(user_id)})
    except NotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))


@router.put("/{group_id}/members/{user_id}/role", response_model=GroupMemberOut)
async def update_role(group_id: uuid.UUID, user_id: uuid.UUID, payload: UpdateRoleRequest, uid: uuid.UUID = Depends(current_user_id), s: GroupsService = Depends(svc)):
    from app.main import bus
    try:
        m = s.update_role(group_id, uid, user_id, payload.role)
        await bus.publish("group.member.role_updated", {"group_id": str(group_id), "user_id": str(user_id), "role": m.role})
        return GroupMemberOut(group_id=m.group_id, user_id=m.user_id, role=m.role)
    except NotFoundError as e:
        raise HTTPException(404, str(e))
    except PermissionDeniedError as e:
        raise HTTPException(403, str(e))
    except ConflictError as e:
        raise HTTPException(409, str(e))
