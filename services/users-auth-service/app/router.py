from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import TokenResponse, UserLogin, UserOut, UserRegister
from app.service import UserService
from groupsapp_shared.security import decode_user_id

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    uid = decode_user_id(token, settings.secret_key, settings.algorithm)
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    user = UserService(db).get(uid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user


router = APIRouter()

auth = APIRouter(prefix="/api/v1/auth", tags=["auth"])
users = APIRouter(prefix="/api/v1/users", tags=["users"])


@auth.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    svc = UserService(db)
    try:
        user = svc.register(payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return TokenResponse(access_token=svc.issue_token(user), user=UserOut.model_validate(user))


@auth.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    svc = UserService(db)
    user = svc.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=svc.issue_token(user), user=UserOut.model_validate(user))


@auth.post("/token", response_model=TokenResponse)
def oauth_token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    svc = UserService(db)
    user = svc.authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=svc.issue_token(user), user=UserOut.model_validate(user))


@users.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return UserOut.model_validate(user)


@users.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    user = UserService(db).get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    return UserOut.model_validate(user)


@users.get("", response_model=list[UserOut])
def search_users(q: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import or_, select
    from app.models import User as UserModel
    stmt = select(UserModel)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(UserModel.username.ilike(like), UserModel.email.ilike(like)))
    stmt = stmt.limit(50)
    results = db.execute(stmt).scalars().all()
    return [UserOut.model_validate(u) for u in results]


router.include_router(auth)
router.include_router(users)
