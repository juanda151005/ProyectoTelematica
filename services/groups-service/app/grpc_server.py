from __future__ import annotations

import logging
import uuid
from concurrent import futures

import grpc

from app.config import get_settings
from app.database import SessionLocal
from app.repository import GroupRepository
from groupsapp_shared.proto_gen import groups_pb2, groups_pb2_grpc

log = logging.getLogger(__name__)
settings = get_settings()


class GroupsServicer(groups_pb2_grpc.GroupsServiceServicer):
    def IsMember(self, request, context):
        db = SessionLocal()
        try:
            repo = GroupRepository(db)
            m = repo.get_member(uuid.UUID(request.group_id), uuid.UUID(request.user_id))
            return groups_pb2.IsMemberResponse(is_member=bool(m), role=m.role if m else "")
        finally:
            db.close()

    def GetGroupMembers(self, request, context):
        db = SessionLocal()
        try:
            ids = GroupRepository(db).list_member_ids(uuid.UUID(request.group_id))
            return groups_pb2.GetGroupMembersResponse(user_ids=[str(i) for i in ids])
        finally:
            db.close()

    def GetGroup(self, request, context):
        db = SessionLocal()
        try:
            g = GroupRepository(db).get_group(uuid.UUID(request.group_id))
            if not g:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return groups_pb2.GroupReply()
            return groups_pb2.GroupReply(
                id=str(g.id),
                name=g.name,
                description=str(g.settings.get("description", "")),
                created_by=str(g.admin_id),
                is_direct=bool(g.settings.get("is_dm", False)),
            )
        finally:
            db.close()


async def serve_grpc() -> None:
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    groups_pb2_grpc.add_GroupsServiceServicer_to_server(GroupsServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{settings.grpc_port}")
    await server.start()
    log.info("gRPC GroupsService listening on :%d", settings.grpc_port)
    await server.wait_for_termination()
