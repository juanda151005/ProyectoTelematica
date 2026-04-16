from __future__ import annotations

import logging
import uuid
from typing import Optional

import grpc

from app.config import get_settings
from groupsapp_shared.proto_gen import groups_pb2, groups_pb2_grpc

log = logging.getLogger(__name__)
settings = get_settings()


class GroupsGRPCClient:
    def __init__(self, addr: str | None = None):
        self.addr = addr or settings.groups_grpc_addr
        self._channel: Optional[grpc.Channel] = None

    def _stub(self) -> groups_pb2_grpc.GroupsServiceStub:
        if self._channel is None:
            self._channel = grpc.insecure_channel(self.addr)
        return groups_pb2_grpc.GroupsServiceStub(self._channel)

    def is_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        try:
            r = self._stub().IsMember(
                groups_pb2.IsMemberRequest(group_id=str(group_id), user_id=str(user_id)), timeout=3.0
            )
            return bool(r.is_member)
        except grpc.RpcError as e:
            log.warning("IsMember gRPC failed: %s", e)
            return False

    def group_members(self, group_id: uuid.UUID) -> list[uuid.UUID]:
        try:
            r = self._stub().GetGroupMembers(
                groups_pb2.GetGroupMembersRequest(group_id=str(group_id)), timeout=3.0
            )
            return [uuid.UUID(u) for u in r.user_ids]
        except grpc.RpcError as e:
            log.warning("GetGroupMembers gRPC failed: %s", e)
            return []
