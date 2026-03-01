from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.presence.repository import PresenceRepository
from app.modules.presence.schemas import PresenceOut
from app.modules.presence.service import PresenceService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/{user_id}/presence', response_model=PresenceOut)
def get_user_presence(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Usuario no encontrado')
    service = PresenceService(PresenceRepository(db))
    presence = service.get_or_create(user_id)
    return PresenceOut(user_id=user_id, is_online=presence.is_online, last_seen=presence.last_seen)
