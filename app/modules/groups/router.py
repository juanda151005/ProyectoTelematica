from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.groups.repository import GroupRepository
from app.modules.groups.schemas import AddMemberRequest, GroupCreateRequest, GroupMemberOut, GroupOut
from app.modules.groups.service import GroupsService
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


@router.post('/{group_id}/members', response_model=GroupMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    group_id: UUID,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = GroupsService(GroupRepository(db), UserRepository(db))
    try:
        member = service.add_member(group_id, current_user.id, payload.username)
        return GroupMemberOut(group_id=member.group_id, user_id=member.user_id, role=member.role)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
