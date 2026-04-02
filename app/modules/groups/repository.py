from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.groups.models import Group, GroupMember


class GroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_group(self, group: Group) -> Group:
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def get_group(self, group_id):
        return self.db.get(Group, group_id)

    def create_member(self, member: GroupMember) -> GroupMember:
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def get_member(self, group_id, user_id):
        stmt = select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_member_ids(self, group_id):
        stmt = select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_user_groups(self, user_id):
        stmt = select(Group).join(GroupMember, Group.id == GroupMember.group_id).where(GroupMember.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_group_members_details(self, group_id):
        from app.modules.users.models import User
        stmt = select(GroupMember.user_id, User.username, GroupMember.role).join(User, GroupMember.user_id == User.id).where(GroupMember.group_id == group_id)
        rows = self.db.execute(stmt).all()
        return [{"user_id": r.user_id, "username": r.username, "role": r.role} for r in rows]

    def delete_member(self, member: GroupMember) -> None:
        self.db.delete(member)
        self.db.commit()

    def find_dm_group(self, user1_id, user2_id):
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(GroupMember.user_id == user1_id)
        )
        user1_groups = self.db.execute(stmt).scalars().all()
        for g in user1_groups:
            if g.settings.get('is_dm') is True:
                # Check if user2 is a member
                if self.get_member(g.id, user2_id):
                    return g
        return None

    def has_messages(self, group_id) -> bool:
        from app.modules.messages.models import Message
        stmt = select(Message.id).where(Message.group_id == group_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def save(self) -> None:
        self.db.commit()
