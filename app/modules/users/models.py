import uuid

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.shared.base_model import Base, TimestampMixin
from app.shared.enums import UserStatus


class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, native_enum=False), default=UserStatus.OFFLINE, nullable=False)

    memberships = relationship('GroupMember', back_populates='user', cascade='all, delete-orphan')
    sent_messages = relationship('Message', back_populates='sender', foreign_keys='Message.sender_id')
    received_direct_messages = relationship('Message', foreign_keys='Message.recipient_id')
    presence = relationship('UserPresence', back_populates='user', uselist=False, cascade='all, delete-orphan')
