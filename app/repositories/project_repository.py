from sqlalchemy import or_, select

from app.models.project_members import ProjectMember
from app.models.projects import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository):
    def create(
        self,
        *,
        name: str,
        slug: str,
        owner_id: int,
        description: str | None = None,
    ) -> Project:
        project = Project(
            name=name, slug=slug, description=description, owner_id=owner_id
        )
        self.db.add(project)
        self.db.flush()
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.get(Project, project_id)

    def get_by_slug(self, slug: str, *, include_archived: bool = True) -> Project | None:
        stmt = select(Project).where(Project.slug == slug)
        if not include_archived:
            stmt = stmt.where(Project.is_archived.is_(False))
        return self.db.scalar(stmt)

    def slug_exists(self, slug: str) -> bool:
        return self.db.scalar(select(Project.id).where(Project.slug == slug)) is not None

    def list_for_user(
        self,
        user_id: int,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        member_projects = select(ProjectMember.project_id).where(
            ProjectMember.user_id == user_id
        )
        stmt = select(Project).where(
            or_(Project.owner_id == user_id, Project.id.in_(member_projects))
        )
        if not include_archived:
            stmt = stmt.where(Project.is_archived.is_(False))
        stmt = stmt.order_by(Project.id).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def list_all(
        self, *, include_archived: bool = False, offset: int = 0, limit: int = 50
    ) -> list[Project]:
        stmt = select(Project)
        if not include_archived:
            stmt = stmt.where(Project.is_archived.is_(False))
        stmt = stmt.order_by(Project.id).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def update(self, project: Project, **fields) -> Project:
        for key, value in fields.items():
            setattr(project, key, value)
        self.db.flush()
        return project

    def soft_delete(self, project: Project) -> Project:
        project.is_archived = True
        self.db.flush()
        return project