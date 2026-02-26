from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    settings: dict = Field(default_factory=dict)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    admin_id: UUID
    settings: dict


class AddMemberRequest(BaseModel):
    username: str


class GroupMemberOut(BaseModel):
    group_id: UUID
    user_id: UUID
    role: str
