from __future__ import annotations

import uuid
from typing import Optional

import bcrypt
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.schemas import UserRegister
from groupsapp_shared.security import create_access_token

settings = get_settings()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, data: UserRegister) -> User:
        email = data.email or f"{data.username}@users.groupsapp.io"
        exists = self.db.execute(
            select(User).where(or_(User.username == data.username, User.email == email))
        ).scalar_one_or_none()
        if exists:
            raise ValueError("username or email already registered")

        user = User(
            username=data.username,
            email=email,
            full_name=data.full_name,
            hashed_password=_hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not user or not _verify_password(password, user.hashed_password):
            return None
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(
            user.id,
            secret_key=settings.secret_key,
            algorithm=settings.algorithm,
            expire_minutes=settings.access_token_expire_minutes,
            extra_claims={"username": user.username},
        )

    def get(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_many(self, user_ids: list[uuid.UUID]) -> list[User]:
        if not user_ids:
            return []
        return list(self.db.execute(select(User).where(User.id.in_(user_ids))).scalars().all())
