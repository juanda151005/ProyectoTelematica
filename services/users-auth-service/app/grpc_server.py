from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent import futures

import grpc

from app.config import get_settings
from app.database import SessionLocal
from app.service import UserService
from groupsapp_shared.proto_gen import users_pb2, users_pb2_grpc
from groupsapp_shared.security import decode_access_token

log = logging.getLogger(__name__)
settings = get_settings()


class UsersServicer(users_pb2_grpc.UsersServiceServicer):
    def ValidateToken(self, request, context):
        payload = decode_access_token(request.token, settings.secret_key, settings.algorithm)
        if not payload:
            return users_pb2.ValidateTokenResponse(valid=False)
        return users_pb2.ValidateTokenResponse(
            valid=True,
            user_id=payload.get("sub", ""),
            username=payload.get("username", ""),
        )

    def GetUser(self, request, context):
        db = SessionLocal()
        try:
            user = UserService(db).get(uuid.UUID(request.user_id))
            if not user:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return users_pb2.UserReply()
            return users_pb2.UserReply(
                id=str(user.id),
                username=user.username,
                email=user.email,
                full_name=user.full_name,
            )
        finally:
            db.close()

    def FindByUsername(self, request, context):
        from sqlalchemy import select
        from app.models import User as UserModel
        db = SessionLocal()
        try:
            u = db.execute(select(UserModel).where(UserModel.username == request.username)).scalar_one_or_none()
            if not u:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return users_pb2.UserReply()
            return users_pb2.UserReply(id=str(u.id), username=u.username, email=u.email, full_name=u.full_name)
        finally:
            db.close()

    def GetUsersBatch(self, request, context):
        db = SessionLocal()
        try:
            ids = [uuid.UUID(u) for u in request.user_ids]
            users = UserService(db).get_many(ids)
            return users_pb2.GetUsersBatchResponse(
                users=[
                    users_pb2.UserReply(
                        id=str(u.id),
                        username=u.username,
                        email=u.email,
                        full_name=u.full_name,
                    )
                    for u in users
                ]
            )
        finally:
            db.close()


async def serve_grpc() -> None:
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    users_pb2_grpc.add_UsersServiceServicer_to_server(UsersServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{settings.grpc_port}")
    await server.start()
    log.info("gRPC UsersService listening on :%d", settings.grpc_port)
    await server.wait_for_termination()
