from app.modules.groups.models import Group, GroupMember
from app.modules.groups.repository import GroupRepository
from app.modules.users.repository import UserRepository
from app.shared.enums import GroupMemberRole
from app.shared.exceptions import ConflictError, NotFoundError, PermissionDeniedError


class GroupsService:
    def __init__(self, groups_repo: GroupRepository, users_repo: UserRepository):
        self.groups_repo = groups_repo
        self.users_repo = users_repo

    def create_group(self, name: str, admin_id, settings: dict) -> Group:
        group = Group(name=name, admin_id=admin_id, settings=settings)
        group = self.groups_repo.create_group(group)
        admin_membership = GroupMember(group_id=group.id, user_id=admin_id, role=GroupMemberRole.ADMIN.value)
        self.groups_repo.create_member(admin_membership)
        return group

    def _ensure_admin(self, group, requester_id):
        membership = self.groups_repo.get_member(group.id, requester_id)
        if not membership or membership.role != GroupMemberRole.ADMIN.value:
            raise PermissionDeniedError('Solo los administradores pueden realizar esta acción')

    def add_member(self, group_id, requester_id, username: str) -> GroupMember:
        group = self.groups_repo.get_group(group_id)
        if not group:
            raise NotFoundError('Grupo no encontrado')
        self._ensure_admin(group, requester_id)

        user = self.users_repo.get_by_username(username)
        if not user:
            raise NotFoundError('Usuario no encontrado')

        exists = self.groups_repo.get_member(group_id, user.id)
        if exists:
            raise ConflictError('El usuario ya pertenece al grupo')

        membership = GroupMember(group_id=group_id, user_id=user.id, role=GroupMemberRole.MEMBER.value)
        return self.groups_repo.create_member(membership)

    def remove_member(self, group_id, requester_id, target_user_id) -> None:
        group = self.groups_repo.get_group(group_id)
        if not group:
            raise NotFoundError('Grupo no encontrado')
        self._ensure_admin(group, requester_id)

        if group.admin_id == target_user_id:
            raise PermissionDeniedError('El creador del grupo no puede ser eliminado')

        target_membership = self.groups_repo.get_member(group_id, target_user_id)
        if not target_membership:
            raise NotFoundError('El usuario no pertenece al grupo')

        self.groups_repo.delete_member(target_membership)

    def update_member_role(self, group_id, requester_id, target_user_id, new_role: str) -> GroupMember:
        group = self.groups_repo.get_group(group_id)
        if not group:
            raise NotFoundError('Grupo no encontrado')
        self._ensure_admin(group, requester_id)

        if group.admin_id == target_user_id:
            raise PermissionDeniedError('El creador del grupo no puede ser modificado')

        target_membership = self.groups_repo.get_member(group_id, target_user_id)
        if not target_membership:
            raise NotFoundError('El usuario no pertenece al grupo')

        if new_role not in [GroupMemberRole.ADMIN.value, GroupMemberRole.MEMBER.value]:
            raise ConflictError('Rol inválido')

        target_membership.role = new_role
        self.groups_repo.save()
        return target_membership

    def ensure_membership(self, group_id, user_id) -> None:
        membership = self.groups_repo.get_member(group_id, user_id)
        if not membership:
            raise PermissionDeniedError('No perteneces a este grupo')

    def get_user_groups(self, user_id) -> list[Group]:
        return self.groups_repo.get_user_groups(user_id)

    def get_group_members(self, group_id, requester_id):
        self.ensure_membership(group_id, requester_id)
        return self.groups_repo.get_group_members_details(group_id)
