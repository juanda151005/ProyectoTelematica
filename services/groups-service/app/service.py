from __future__ import annotations

import uuid

from app.clients import UsersGRPCClient
from app.models import Group, GroupMember
from app.repository import GroupRepository


class NotFoundError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class ConflictError(Exception):
    pass


ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"


class GroupsService:
    def __init__(self, repo: GroupRepository, users: UsersGRPCClient):
        self.repo = repo
        self.users = users

    def create_group(self, name: str, admin_id: uuid.UUID, settings: dict) -> Group:
        group = Group(name=name, admin_id=admin_id, settings=settings)
        group = self.repo.create_group(group)
        self.repo.create_member(GroupMember(group_id=group.id, user_id=admin_id, role=ROLE_ADMIN))
        return group

    def _ensure_admin(self, group: Group, requester_id: uuid.UUID) -> None:
        m = self.repo.get_member(group.id, requester_id)
        if not m or m.role != ROLE_ADMIN:
            raise PermissionDeniedError("Solo los administradores pueden realizar esta acción")

    def add_member_by_username(self, group_id: uuid.UUID, requester_id: uuid.UUID, username: str) -> tuple[GroupMember, dict]:
        group = self.repo.get_group(group_id)
        if not group:
            raise NotFoundError("Grupo no encontrado")
        if group.settings.get("is_dm"):
            raise PermissionDeniedError("No puedes agregar miembros a un chat privado")
        self._ensure_admin(group, requester_id)

        user = self.users.find_by_username(username)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        uid = uuid.UUID(user["id"])

        if self.repo.get_member(group_id, uid):
            raise ConflictError("El usuario ya pertenece al grupo")

        member = self.repo.create_member(GroupMember(group_id=group_id, user_id=uid, role=ROLE_MEMBER))
        return member, user

    def remove_member(self, group_id: uuid.UUID, requester_id: uuid.UUID, target_id: uuid.UUID) -> None:
        group = self.repo.get_group(group_id)
        if not group:
            raise NotFoundError("Grupo no encontrado")

        if group.settings.get("is_dm"):
            if requester_id != target_id:
                raise PermissionDeniedError("En un chat privado solo puedes eliminarte a ti mismo")
        else:
            self._ensure_admin(group, requester_id)
            if group.admin_id == target_id:
                raise PermissionDeniedError("El creador del grupo no puede ser eliminado")

        m = self.repo.get_member(group_id, target_id)
        if not m:
            raise NotFoundError("El usuario no pertenece al grupo")
        self.repo.delete_member(m)

    def update_role(self, group_id: uuid.UUID, requester_id: uuid.UUID, target_id: uuid.UUID, role: str) -> GroupMember:
        group = self.repo.get_group(group_id)
        if not group:
            raise NotFoundError("Grupo no encontrado")
        if group.settings.get("is_dm"):
            raise PermissionDeniedError("Los chats privados no tienen administradores")
        self._ensure_admin(group, requester_id)
        if group.admin_id == target_id:
            raise PermissionDeniedError("El creador del grupo no puede ser modificado")
        m = self.repo.get_member(group_id, target_id)
        if not m:
            raise NotFoundError("El usuario no pertenece al grupo")
        if role not in (ROLE_ADMIN, ROLE_MEMBER):
            raise ConflictError("Rol inválido")
        m.role = role
        self.repo.save()
        return m

    def ensure_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not self.repo.get_member(group_id, user_id):
            raise PermissionDeniedError("No perteneces a este grupo")

    def list_user_groups(self, user_id: uuid.UUID) -> list[Group]:
        groups = self.repo.get_user_groups(user_id)
        out = []
        for g in groups:
            if g.settings.get("is_dm"):
                if g.last_message_at is None:
                    continue
                # Replace display name with the other user's username
                member_ids = self.repo.list_member_ids(g.id)
                other = next((mid for mid in member_ids if mid != user_id), None)
                if other:
                    info = self.users.get_user(other)
                    if info:
                        g.name = info["username"]
            out.append(g)
        return out

    def get_or_create_dm(self, requester_id: uuid.UUID, target_id: uuid.UUID) -> Group:
        if requester_id == target_id:
            raise ConflictError("No puedes crear un chat privado contigo mismo")
        target = self.users.get_user(target_id)
        if not target:
            raise NotFoundError("Usuario no encontrado")

        existing = self.repo.find_dm_between(requester_id, target_id)
        if existing:
            return existing

        dm = Group(name="Chat Privado", admin_id=requester_id, settings={"is_dm": True})
        dm = self.repo.create_group(dm)
        self.repo.create_member(GroupMember(group_id=dm.id, user_id=requester_id, role=ROLE_MEMBER))
        self.repo.create_member(GroupMember(group_id=dm.id, user_id=target_id, role=ROLE_MEMBER))
        return dm

    def members_detail(self, group_id: uuid.UUID, requester_id: uuid.UUID) -> list[dict]:
        self.ensure_member(group_id, requester_id)
        members = self.repo.list_members(group_id)
        infos = self.users.get_users_batch([m.user_id for m in members])
        out = []
        for m in members:
            info = infos.get(str(m.user_id), {"username": "?"})
            out.append({"user_id": m.user_id, "username": info.get("username", "?"), "role": m.role})
        return out
