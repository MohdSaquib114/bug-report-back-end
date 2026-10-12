from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.bugs import BugPriority, StatusEnum


class ScreenSize(BaseModel):
    width: int
    height: int


class ScreenshotItem(BaseModel):
    id: str
    dataUrl: str
    createdAt: int


class BugReportMetadata(BaseModel):
    url: str
    userAgent: str
    timestamp: str | None = None
    screenSize: ScreenSize


class BugReportData(BaseModel):
    """Exact shape posted by the embeddable widget.

    The widget POSTs this body to the URL configured as ``projectUrl``
    (``POST /projects/{slug}/bugs``).
    """

    projectUrl: str
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    screenshots: list[ScreenshotItem] = Field(default_factory=list, max_length=3)
    timestamp: str
    meta: BugReportMetadata


class BugCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: BugPriority = BugPriority.MEDIUM
    assignee_id: int | None = None


class BugUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: StatusEnum | None = None
    priority: BugPriority | None = None
    assignee_id: int | None = None
    resolved_at: datetime | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str | None
    url: str
    storage_key: str | None = None
    content_type: str | None
    size_bytes: int | None
    created_at: datetime


class BugOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: StatusEnum
    priority: BugPriority
    project_id: int
    reporter_id: int | None
    assignee_id: int | None
    ip_address: str | None
    location: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BugDetailOut(BugOut):
    attachments: list[AttachmentOut] = Field(default_factory=list)


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)
    parent_id: int | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    bug_id: int
    author_id: int | None
    parent_id: int | None
    is_edited: bool
    created_at: datetime
    updated_at: datetime