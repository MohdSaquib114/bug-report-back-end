from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_optional_user
from app.models.bugs import Bug, BugPriority, StatusEnum
from app.models.comments import Comment
from app.models.users import User
from app.schemas.bug import (
    AttachmentOut,
    BugDetailOut,
    BugOut,
    BugReportData,
    BugUpdate,
    CommentCreate,
    CommentOut,
)
from app.services.bug_service import BugService
from config.database import get_db

router = APIRouter(tags=["bugs"])


@router.post(
    "/projects/{slug}/bugs",
    response_model=BugOut,
    status_code=status.HTTP_201_CREATED,
)
def report_bug(
    slug: str,
    data: BugReportData,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> Bug:
    """Public endpoint used by the embeddable widget.

    The widget POSTs the full ``BugReportData`` body (title, description,
    up to 3 screenshots, timestamp and metadata) to ``/projects/{slug}/bugs``.
    Auth is optional; when a bearer token is present the report is attributed
    to that user.
    """
    ip_address = request.client.host if request.client else None
    return BugService(db).report(
        slug,
        data,
        reporter_id=user.id if user else None,
        ip_address=ip_address,
    )


@router.get("/projects/{slug}/bugs", response_model=list[BugOut])
def list_bugs(
    slug: str,
    status_filter: StatusEnum | None = Query(default=None, alias="status"),
    priority: BugPriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    reporter_id: int | None = Query(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Bug]:
    return BugService(db).list(
        slug,
        user,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        offset=offset,
        limit=limit,
    )


@router.get("/bugs/{bug_id}", response_model=BugDetailOut)
def get_bug(
    bug_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bug:
    return BugService(db).get(bug_id, user)


@router.patch("/bugs/{bug_id}", response_model=BugOut)
def update_bug(
    bug_id: int,
    data: BugUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bug:
    return BugService(db).update(bug_id, data, user)


@router.delete("/bugs/{bug_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bug(
    bug_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    BugService(db).delete(bug_id, user)


@router.get("/bugs/{bug_id}/comments", response_model=list[CommentOut])
def list_comments(
    bug_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Comment]:
    return BugService(db).list_comments(bug_id, user)


@router.post(
    "/bugs/{bug_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    bug_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Comment:
    return BugService(db).add_comment(bug_id, data, user)


@router.get("/bugs/{bug_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(
    bug_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return BugService(db).list_attachments(bug_id, user)


@router.post(
    "/bugs/{bug_id}/attachments",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    bug_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a file; it is stored in the bucket and its URL is persisted."""
    data = await file.read()
    return BugService(db).upload_attachment(
        bug_id,
        data=data,
        content_type=file.content_type,
        filename=file.filename,
        user=user,
    )