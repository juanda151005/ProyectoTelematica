from enum import Enum


class UserStatus(str, Enum):
    ONLINE = 'online'
    OFFLINE = 'offline'


class GroupMemberRole(str, Enum):
    ADMIN = 'admin'
    MEMBER = 'member'


class MessageType(str, Enum):
    TEXT = 'text'
    FILE = 'file'
    IMAGE = 'image'
