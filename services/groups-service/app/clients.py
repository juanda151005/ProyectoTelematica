"""gRPC client to users-auth-service."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

import grpc

from app.config import get_settings
from groupsapp_shared.proto_gen import users_pb2, users_pb2_grpc

log = logging.getLogger(__name__)
settings = get_settings()


class UsersGRPCClient:
    def __init__(self, addr: str | None = None):
        self.addr = addr or settings.users_grpc_addr
        self._channel: Optional[grpc.Channel] = None

    def _stub(self) -> users_pb2_grpc.UsersServiceStub:
        if self._channel is None:
            self._channel = grpc.insecure_channel(self.addr)
        return users_pb2_grpc.UsersServiceStub(self._channel)

    def get_user(self, user_id: uuid.UUID) -> Optional[dict]:
        try:
            resp = self._stub().GetUser(users_pb2.GetUserRequest(user_id=str(user_id)), timeout=3.0)
            if not resp.id:
                return None
            return {"id": resp.id, "username": resp.username, "email": resp.email, "full_name": resp.full_name}
        except grpc.RpcError as e:
            log.warning("GetUser gRPC failed: %s", e)
            return None

    def get_users_batch(self, user_ids: list[uuid.UUID]) -> dict[str, dict]:
        try:
            resp = self._stub().GetUsersBatch(
                users_pb2.GetUsersBatchRequest(user_ids=[str(u) for u in user_ids]), timeout=3.0
            )
            return {
                u.id: {"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name}
                for u in resp.users
            }
        except grpc.RpcError as e:
            log.warning("GetUsersBatch gRPC failed: %s", e)
            return {}

    def find_by_username(self, username: str) -> Optional[dict]:
        try:
            resp = self._stub().FindByUsername(users_pb2.FindByUsernameRequest(username=username), timeout=3.0)
            if not resp.id:
                return None
            return {"id": resp.id, "username": resp.username, "email": resp.email, "full_name": resp.full_name}
        except grpc.RpcError as e:
            log.warning("FindByUsername gRPC failed: %s", e)
            return None
