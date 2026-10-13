import json

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_optional_user
from app.errors import ValidationFailure
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

MAX_SCREENSHOTS = 3
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024


@router.post(
    "/projects/{slug}/bugs",
    response_model=BugOut,
    status_code=status.HTTP_201_CREATED,
)
async def report_bug(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> Bug:
    """Public endpoint used by the embeddable widget.

    Accepts either:

    * ``application/json`` — the full ``BugReportData`` body with base64
      ``data:`` URL screenshots (kept for backwards compatibility), or
    * ``multipart/form-data`` — ``title``, ``description``, optional
      ``timestamp``/``meta`` and up to 3 ``screenshots`` image files.

    Auth is optional; when a bearer token is present the report is attributed
    to that user.
    """
    ip_address = request.client.host if request.client else None
    service = BugService(db)
    reporter_id = user.id if user else None
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        return await _report_multipart(
            service,
            slug,
            request,
            reporter_id=reporter_id,
            ip_address=ip_address,
        )

    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise ValidationFailure("Request body must be valid JSON") from exc
    try:
        data = BugReportData.model_validate(payload)
    except ValidationError as exc:
        raise ValidationFailure("Invalid bug report payload") from exc

    return service.report(
        slug,
        data,
        reporter_id=reporter_id,
        ip_address=ip_address,
    )


async def _report_multipart(
    service: BugService,
    slug: str,
    request: Request,
    *,
    reporter_id: int | None,
    ip_address: str | None,
) -> Bug:
    form = await request.form()

    title = str(form.get("title") or "").strip()
    description = str(form.get("description") or "").strip()
    if not title:
        raise ValidationFailure("Title is required")
    if not description:
        raise ValidationFailure("Description is required")

    location = None
    meta_raw = form.get("meta")
    if meta_raw:
        try:
            location = json.loads(str(meta_raw)).get("url")
        except (AttributeError, TypeError, ValueError):
            location = None

    files = [value for value in form.getlist("screenshots") if hasattr(value, "read")]
    if len(files) > MAX_SCREENSHOTS:
        raise ValidationFailure(
            "At most {0} screenshots are allowed".format(MAX_SCREENSHOTS)
        )

    screenshots: list[tuple[str | None, str, bytes]] = []
    for item in files:
        content_type = (item.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise ValidationFailure("Screenshots must be image files")
        data = await item.read()
        if not data:
            continue
        if len(data) > MAX_SCREENSHOT_BYTES:
            raise ValidationFailure("A screenshot exceeds the 8 MB limit")
        screenshots.append((item.filename, content_type, data))

    return service.report_multipart(
        slug,
        title=title,
        description=description,
        screenshots=screenshots,
        location=location,
        reporter_id=reporter_id,
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