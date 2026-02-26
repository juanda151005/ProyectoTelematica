from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.users.repository import UserRepository

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f'{settings.api_prefix}/auth/token')


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido')

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Usuario no encontrado')
    return user
