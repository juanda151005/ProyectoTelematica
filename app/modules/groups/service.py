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

    def add_member(self, group_id, requester_id, username: str) -> GroupMember:
        group = self.groups_repo.get_group(group_id)
        if not group:
            raise NotFoundError('Grupo no encontrado')
        if group.admin_id != requester_id:
            raise PermissionDeniedError('Solo el admin puede agregar miembros')

        user = self.users_repo.get_by_username(username)
        if not user:
            raise NotFoundError('Usuario no encontrado')

        exists = self.groups_repo.get_member(group_id, user.id)
        if exists:
            raise ConflictError('El usuario ya pertenece al grupo')

        membership = GroupMember(group_id=group_id, user_id=user.id, role=GroupMemberRole.MEMBER.value)
        return self.groups_repo.create_member(membership)

    def ensure_membership(self, group_id, user_id) -> None:
        membership = self.groups_repo.get_member(group_id, user_id)
        if not membership:
            raise PermissionDeniedError('No perteneces a este grupo')
