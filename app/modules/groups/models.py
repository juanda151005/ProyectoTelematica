import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.shared.base_model import Base, TimestampMixin
from app.shared.enums import GroupMemberRole


class Group(Base, TimestampMixin):
    __tablename__ = 'groups'

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    admin_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    settings: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, 'postgresql'), default=dict, nullable=False)

    members = relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    messages = relationship('Message', back_populates='group', cascade='all, delete-orphan')


class GroupMember(Base):
    __tablename__ = 'group_members'
    __table_args__ = (UniqueConstraint('group_id', 'user_id', name='uq_group_member'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default=GroupMemberRole.MEMBER.value, nullable=False)

    group = relationship('Group', back_populates='members')
    user = relationship('User', back_populates='memberships')
