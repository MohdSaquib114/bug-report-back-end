from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.project_members import ProjectRole


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, max_length=255)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    is_archived: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ProjectMemberCreate(BaseModel):
    email: str
    role: ProjectRole = ProjectRole.CONTRIBUTOR


class ProjectMemberUpdate(BaseModel):
    role: ProjectRole


class ProjectMemberUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: ProjectRole
    created_at: datetime
    user: ProjectMemberUser