from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.modules.presence.repository import PresenceRepository
from app.modules.presence.schemas import PresenceOut
from app.modules.presence.service import PresenceService
from app.modules.users.models import User

router = APIRouter(prefix='/users', tags=['users'])


@router.get('/me/presence', response_model=PresenceOut)
def get_my_presence(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = PresenceService(PresenceRepository(db))
    presence = service.get_or_create(current_user.id)
    return PresenceOut(user_id=current_user.id, is_online=presence.is_online, last_seen=presence.last_seen)
