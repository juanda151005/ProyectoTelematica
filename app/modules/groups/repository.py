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
