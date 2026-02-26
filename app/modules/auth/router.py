from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.auth.service import AuthService
from app.modules.presence.repository import PresenceRepository
from app.modules.presence.service import PresenceService
from app.modules.users.repository import UserRepository
from app.shared.enums import UserStatus
from app.shared.exceptions import ConflictError, PermissionDeniedError

router = APIRouter(prefix='/auth', tags=['auth'])


def _issue_token(username: str, password: str, db: Session) -> TokenResponse:
    service = AuthService(UserRepository(db))
    token = service.login(username, password)
    user = UserRepository(db).get_by_username(username)
    if user:
        PresenceService(PresenceRepository(db)).set_online(user.id)
        user.status = UserStatus.ONLINE
        db.commit()
    return TokenResponse(access_token=token)


@router.post('/register', response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(UserRepository(db))
    try:
        user = service.register(payload.username, payload.password)
        # Login inmediato para simplificar flujo en MVP.
        token = service.login(payload.username, payload.password)
        PresenceService(PresenceRepository(db)).set_online(user.id)
        user.status = UserStatus.ONLINE
        db.commit()
        return TokenResponse(access_token=token)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return _issue_token(payload.username, payload.password, db)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post('/token', response_model=TokenResponse, include_in_schema=False)
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Endpoint para OAuth2 Password Flow usado por el botón "Authorize" de Swagger.
    try:
        return _issue_token(form_data.username, form_data.password, db)
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
