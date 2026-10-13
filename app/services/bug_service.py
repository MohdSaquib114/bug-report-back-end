import base64
import binascii

from sqlalchemy.orm import Session

from app.errors import ForbiddenError, NotFoundError, ValidationFailure
from app.models.activity import ActivityType
from app.models.attachments import Attachment
from app.models.bugs import Bug, BugPriority, StatusEnum
from app.models.comments import Comment
from app.models.users import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.base import utcnow
from app.repositories.bug_repository import BugRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.bug import BugCreate, BugReportData, BugUpdate, CommentCreate
from app.services.permission_service import PermissionService
from app.services.storage_service import StorageError, get_storage


def _decode_data_url(data_url: str) -> tuple[str, bytes | None]:
    """Return (content_type, decoded_bytes) for a ``data:`` URL."""
    if not data_url.startswith("data:"):
        return "image/png", None
    header, _, payload = data_url.partition(",")
    media = header[5:].split(";")[0] or "image/png"
    try:
        raw = base64.b64decode(payload + "=" * (-len(payload) % 4))
    except (binascii.Error, ValueError):
        return media, None
    return media, raw


class BugService:
    def __init__(self, db: Session):
        self.db = db
        self.bugs = BugRepository(db)
        self.projects = ProjectRepository(db)
        self.attachments = AttachmentRepository(db)
        self.comments = CommentRepository(db)
        self.activities = ActivityRepository(db)
        self.users = UserRepository(db)
        self.permissions = PermissionService(db)

    # ------------------------------------------------------------------
    # Public (widget) reporting
    # ------------------------------------------------------------------
    def report(
        self,
        slug: str,
        data: BugReportData,
        *,
        reporter_id: int | None = None,
        ip_address: str | None = None,
    ) -> Bug:
        project = self.projects.get_by_slug(slug, include_archived=False)
        if project is None:
            raise NotFoundError("Project not found")

        bug = self.bugs.create(
            title=data.title,
            description=data.description,
            project_id=project.id,
            reporter_id=reporter_id,
            ip_address=ip_address,
            location=data.meta.url,
        )
        for shot in data.screenshots:
            self._store_attachment(
                bug=bug,
                filename="{0}.png".format(shot.id),
                data_url=shot.dataUrl,
                uploaded_by_id=reporter_id,
            )
        self._log(bug, None, ActivityType.CREATED, new_value=bug.status.value)
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def report_multipart(
        self,
        slug: str,
        *,
        title: str,
        description: str,
        screenshots: list[tuple[str | None, str, bytes]],
        location: str | None = None,
        reporter_id: int | None = None,
        ip_address: str | None = None,
    ) -> Bug:
        """Create a widget report from already-decoded multipart image files.

        ``screenshots`` items are ``(filename, content_type, data)`` tuples.
        Files are handed to the storage service instead of being carried as
        base64 strings inside a JSON body.
        """
        project = self.projects.get_by_slug(slug, include_archived=False)
        if project is None:
            raise NotFoundError("Project not found")

        bug = self.bugs.create(
            title=title,
            description=description,
            project_id=project.id,
            reporter_id=reporter_id,
            ip_address=ip_address,
            location=location,
        )
        for filename, content_type, data in screenshots:
            self._store_attachment(
                bug=bug,
                filename=filename or "screenshot-{0}.jpg".format(bug.id),
                source_bytes=data,
                content_type=content_type,
                uploaded_by_id=reporter_id,
            )
        self._log(bug, None, ActivityType.CREATED, new_value=bug.status.value)
        self.db.commit()
        self.db.refresh(bug)
        return bug

    # ------------------------------------------------------------------
    # Private bug management
    # ------------------------------------------------------------------
    def _get_project(self, slug: str):
        project = self.projects.get_by_slug(slug, include_archived=False)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    def _get_bug(self, bug_id: int, *, with_attachments: bool = False) -> Bug:
        bug = self.bugs.get_by_id(bug_id, with_attachments=with_attachments)
        if bug is None:
            raise NotFoundError("Bug not found")
        return bug

    def create(self, slug: str, data: BugCreate, user: User) -> Bug:
        project = self._get_project(slug)
        if not self.permissions.can_create_bug(user, project):
            raise ForbiddenError("You cannot report bugs for this project")
        if data.assignee_id is not None and self.users.get_by_id(data.assignee_id) is None:
            raise NotFoundError("Assignee not found")

        bug = self.bugs.create(
            title=data.title,
            description=data.description,
            priority=data.priority,
            project_id=project.id,
            reporter_id=user.id,
            assignee_id=data.assignee_id,
        )
        self._log(bug, user, ActivityType.CREATED, new_value=bug.status.value)
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def list(
        self,
        slug: str,
        user: User,
        *,
        status: StatusEnum | None = None,
        priority: BugPriority | None = None,
        assignee_id: int | None = None,
        reporter_id: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Bug]:
        project = self._get_project(slug)
        if not self.permissions.can_view_project(user, project):
            raise ForbiddenError("You do not have access to this project's bugs")
        return self.bugs.list_by_project(
            project.id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            reporter_id=reporter_id,
            offset=offset,
            limit=limit,
        )

    def get(self, bug_id: int, user: User) -> Bug:
        bug = self._get_bug(bug_id, with_attachments=True)
        if not self.permissions.can_view_bug(user, bug):
            raise ForbiddenError("You do not have access to this bug")
        return bug

    def update(self, bug_id: int, data: BugUpdate, user: User) -> Bug:
        bug = self._get_bug(bug_id)
        if not self.permissions.can_update_bug(user, bug):
            raise ForbiddenError("You cannot update this bug")

        fields = data.model_dump(exclude_unset=True)

        if "assignee_id" in fields and fields["assignee_id"] is not None:
            if self.users.get_by_id(fields["assignee_id"]) is None:
                raise NotFoundError("Assignee not found")

        old_status = bug.status
        old_priority = bug.priority
        old_assignee = bug.assignee_id

        if "status" in fields:
            new_status = fields["status"]
            if new_status in (StatusEnum.RESOLVED, StatusEnum.CLOSED):
                fields["resolved_at"] = bug.resolved_at or utcnow()
            else:
                fields["resolved_at"] = None

        self.bugs.update(bug, **fields)

        if "status" in fields and fields["status"] != old_status:
            self._log(
                bug,
                user,
                ActivityType.STATUS_CHANGED,
                old_value=old_status.value,
                new_value=bug.status.value,
            )
        if "priority" in fields and fields["priority"] != old_priority:
            self._log(
                bug,
                user,
                ActivityType.PRIORITY_CHANGED,
                old_value=old_priority.value,
                new_value=bug.priority.value,
            )
        if "assignee_id" in fields and fields["assignee_id"] != old_assignee:
            self._log(
                bug,
                user,
                ActivityType.ASSIGNED,
                old_value=str(old_assignee) if old_assignee else None,
                new_value=str(bug.assignee_id) if bug.assignee_id else None,
            )

        self.db.commit()
        self.db.refresh(bug)
        return bug

    def delete(self, bug_id: int, user: User) -> None:
        bug = self._get_bug(bug_id)
        if not self.permissions.can_delete_bug(user, bug):
            raise ForbiddenError("You cannot delete this bug")
        self.bugs.delete(bug)
        self.db.commit()

    # ------------------------------------------------------------------
    # Comments / attachments
    # ------------------------------------------------------------------
    def add_comment(self, bug_id: int, data: CommentCreate, user: User) -> Comment:
        bug = self._get_bug(bug_id)
        if not self.permissions.can_view_bug(user, bug):
            raise ForbiddenError("You do not have access to this bug")
        if data.parent_id is not None:
            parent = self.comments.get_by_id(data.parent_id)
            if parent is None or parent.bug_id != bug.id:
                raise NotFoundError("Parent comment not found")
        comment = self.comments.create(
            bug_id=bug.id,
            body=data.body,
            author_id=user.id,
            parent_id=data.parent_id,
        )
        self._log(bug, user, ActivityType.COMMENTED)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_comments(self, bug_id: int, user: User) -> list[Comment]:
        bug = self._get_bug(bug_id)
        if not self.permissions.can_view_bug(user, bug):
            raise ForbiddenError("You do not have access to this bug")
        return self.comments.list_by_bug(bug.id)

    def list_attachments(self, bug_id: int, user: User) -> list:
        bug = self._get_bug(bug_id)
        if not self.permissions.can_view_bug(user, bug):
            raise ForbiddenError("You do not have access to this bug")
        attachments = self.attachments.list_by_bug(bug.id)
        storage = get_storage()
        if storage.configured:
            for attachment in attachments:
                if attachment.storage_key:
                    attachment.url = storage.generate_url(attachment.storage_key)
        return attachments

    def upload_attachment(
        self,
        bug_id: int,
        *,
        data: bytes,
        content_type: str | None,
        filename: str | None,
        user: User,
    ) -> Attachment:
        """Attach a directly uploaded file (multipart) to a bug."""
        bug = self._get_bug(bug_id)
        if not self.permissions.can_create_bug(user, bug.project):
            raise ForbiddenError("You cannot attach files to this bug")
        if not data:
            raise ValidationFailure("The uploaded file is empty")

        attachment = self._store_attachment(
            bug=bug,
            filename=filename,
            source_bytes=data,
            content_type=content_type,
            uploaded_by_id=user.id,
            require_storage=True,
        )
        self._log(bug, user, ActivityType.ATTACHMENT_ADDED, new_value=attachment.filename)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _store_attachment(
        self,
        *,
        bug: Bug,
        filename: str | None,
        uploaded_by_id: int | None,
        data_url: str | None = None,
        source_bytes: bytes | None = None,
        content_type: str | None = None,
        require_storage: bool = False,
    ) -> Attachment:
        storage = get_storage()

        raw = source_bytes
        if raw is None and data_url is not None:
            detected, decoded = _decode_data_url(data_url)
            content_type = content_type or detected
            raw = decoded
        content_type = content_type or "application/octet-stream"

        url = ""
        key: str | None = None
        size: int | None = None

        if storage.configured and raw is not None:
            stored = storage.upload(
                data=raw,
                content_type=content_type,
                prefix="bugs/{0}".format(bug.id),
                filename=filename,
            )
            url, key, size = stored.url, stored.key, len(raw)
        elif require_storage:
            raise StorageError("Attachment storage is not configured")
        elif data_url:
            # Fall back to the inline data URL when no bucket is set.
            url = data_url
            size = len(raw) if raw is not None else len(data_url)
        elif raw is not None:
            # Multipart uploads have no data URL, so build one for the fallback.
            encoded = base64.b64encode(raw).decode("ascii")
            url = "data:{0};base64,{1}".format(content_type, encoded)
            size = len(raw)
        else:
            url = ""
            size = None

        return self.attachments.create(
            bug_id=bug.id,
            url=url,
            storage_key=key,
            filename=filename,
            content_type=content_type,
            size_bytes=size,
            uploaded_by_id=uploaded_by_id,
        )

    def _log(
        self,
        bug: Bug,
        user: User | None,
        activity: ActivityType,
        *,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> None:
        self.activities.create(
            bug_id=bug.id,
            actor_id=user.id if user is not None else None,
            activity_type=activity,
            old_value=old_value,
            new_value=new_value,
        )