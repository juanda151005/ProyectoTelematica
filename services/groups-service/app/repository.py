from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, GroupMember


class GroupRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_group(self, group: Group) -> Group:
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def get_group(self, group_id: uuid.UUID):
        return self.db.get(Group, group_id)

    def create_member(self, member: GroupMember) -> GroupMember:
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def get_member(self, group_id: uuid.UUID, user_id: uuid.UUID):
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_member_ids(self, group_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(GroupMember.user_id).where(GroupMember.group_id == group_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_members(self, group_id: uuid.UUID) -> list[GroupMember]:
        stmt = select(GroupMember).where(GroupMember.group_id == group_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_user_groups(self, user_id: uuid.UUID) -> list[Group]:
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(GroupMember.user_id == user_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def delete_member(self, member: GroupMember) -> None:
        self.db.delete(member)
        self.db.commit()

    def find_dm_between(self, u1: uuid.UUID, u2: uuid.UUID):
        stmt = (
            select(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .where(GroupMember.user_id == u1)
        )
        for g in self.db.execute(stmt).scalars().all():
            if g.settings.get("is_dm") and self.get_member(g.id, u2):
                return g
        return None

    def touch_last_message(self, group_id: uuid.UUID, ts) -> None:
        g = self.db.get(Group, group_id)
        if g is not None:
            g.last_message_at = ts
            self.db.commit()

    def save(self) -> None:
        self.db.commit()
