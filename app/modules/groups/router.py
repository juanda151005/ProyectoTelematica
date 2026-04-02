from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.groups.repository import GroupRepository
from app.modules.groups.schemas import AddMemberRequest, GroupCreateRequest, GroupMemberOut, GroupOut, GroupMemberDetailOut, UpdateRoleRequest
from app.modules.groups.service import GroupsService
from app.modules.messages.websocket import ws_manager
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.exceptions import ConflictError, NotFoundError, PermissionDeniedError

router = APIRouter(prefix='/groups', tags=['groups'])

@router.post('', response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    group = service.create_group(payload.name, current_user.id, payload.settings)
    return group


@router.get('', response_model=list[GroupOut])
def get_user_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    return service.get_user_groups(current_user.id)


@router.post('/{group_id}/members', response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: UUID,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    try:
        member = service.add_member(group_id, current_user.id, payload.username)
        # Notify via websocket
        user_repo = UserRepository(db)
        user = user_repo.get_by_username(payload.username)
        if user:
            await ws_manager.broadcast(group_id, {
                'event': 'member_added',
                'data': {'user_id': str(user.id), 'username': user.username, 'role': member.role}
            })
        return GroupMemberOut(group_id=member.group_id, user_id=member.user_id, role=member.role)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get('/{group_id}/members', response_model=list[GroupMemberDetailOut])
def get_group_members(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    try:
        return service.get_group_members(group_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

@router.delete('/{group_id}/members/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    try:
        service.remove_member(group_id, current_user.id, user_id)
        await ws_manager.broadcast(group_id, {
            'event': 'member_removed',
            'data': {'user_id': str(user_id)}
        })
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

@router.put('/{group_id}/members/{user_id}/role', response_model=GroupMemberOut)
async def update_member_role(
    group_id: UUID,
    user_id: UUID,
    payload: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    try:
        member = service.update_member_role(group_id, current_user.id, user_id, payload.role)
        await ws_manager.broadcast(group_id, {
            'event': 'member_updated',
            'data': {'user_id': str(user_id), 'role': member.role}
        })
        return GroupMemberOut(group_id=member.group_id, user_id=member.user_id, role=member.role)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
