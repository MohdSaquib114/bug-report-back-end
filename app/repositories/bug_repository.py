from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.bugs import Bug, BugPriority, StatusEnum
from app.repositories.base import BaseRepository


class BugRepository(BaseRepository):
    def create(
        self,
        *,
        title: str,
        project_id: int,
        description: str | None = None,
        status: StatusEnum = StatusEnum.OPEN,
        priority: BugPriority = BugPriority.MEDIUM,
        reporter_id: int | None = None,
        assignee_id: int | None = None,
        ip_address: str | None = None,
        location: str | None = None,
    ) -> Bug:
        bug = Bug(
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            reporter_id=reporter_id,
            assignee_id=assignee_id,
            ip_address=ip_address,
            location=location,
        )
        self.db.add(bug)
        self.db.flush()
        return bug

    def get_by_id(self, bug_id: int, *, with_attachments: bool = False) -> Bug | None:
        stmt = select(Bug).where(Bug.id == bug_id)
        if with_attachments:
            stmt = stmt.options(selectinload(Bug.attachments))
        return self.db.scalar(stmt)

    def list_by_project(
        self,
        project_id: int,
        *,
        status: StatusEnum | None = None,
        priority: BugPriority | None = None,
        assignee_id: int | None = None,
        reporter_id: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Bug]:
        stmt = select(Bug).where(Bug.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Bug.status == status)
        if priority is not None:
            stmt = stmt.where(Bug.priority == priority)
        if assignee_id is not None:
            stmt = stmt.where(Bug.assignee_id == assignee_id)
        if reporter_id is not None:
            stmt = stmt.where(Bug.reporter_id == reporter_id)
        stmt = stmt.order_by(Bug.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def update(self, bug: Bug, **fields) -> Bug:
        for key, value in fields.items():
            setattr(bug, key, value)
        self.db.flush()
        return bug