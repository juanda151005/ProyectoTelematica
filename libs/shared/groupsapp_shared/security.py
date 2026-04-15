"""JWT utilities shared by all microservices.

Stateless auth: every service decodes the JWT locally using the shared
SECRET_KEY. Only users-auth-service issues tokens.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt


def create_access_token(
    user_id: UUID | str,
    secret_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 60,
    extra_claims: Optional[dict] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str, secret_key: str, algorithm: str = "HS256"
) -> Optional[dict]:
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return None


def decode_user_id(token: str, secret_key: str, algorithm: str = "HS256") -> Optional[UUID]:
    payload = decode_access_token(token, secret_key, algorithm)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return UUID(sub)
    except ValueError:
        return None
