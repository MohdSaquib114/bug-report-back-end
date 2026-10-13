from sqlalchemy.orm import Session

from app.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.project_members import ProjectMember, ProjectRole
from app.models.projects import Project
from app.models.users import User
from app.repositories.member_repository import MemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectUpdate,
)
from app.services.permission_service import PermissionService
from app.utils import random_suffix, slugify


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.members = MemberRepository(db)
        self.users = UserRepository(db)
        self.permissions = PermissionService(db)

    def _unique_slug(self, name: str) -> str:
        base = slugify(name)
        if not self.projects.slug_exists(base):
            return base
        while True:
            candidate = "{0}-{1}".format(base, random_suffix())
            if not self.projects.slug_exists(candidate):
                return candidate

    def create(self, user: User, data: ProjectCreate) -> Project:
        project = self.projects.create(
            name=data.name,
            slug=self._unique_slug(data.name),
            description=data.description,
            owner_id=user.id,
        )
        self.members.add(
            project_id=project.id, user_id=user.id, role=ProjectRole.OWNER
        )
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(
        self,
        user: User,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        if self.permissions.is_admin(user):
            return self.projects.list_all(
                include_archived=include_archived, offset=offset, limit=limit
            )
        return self.projects.list_for_user(
            user.id,
            include_archived=include_archived,
            offset=offset,
            limit=limit,
        )

    def get(self, slug: str, user: User, *, include_archived: bool = True) -> Project:
        project = self.projects.get_by_slug(slug, include_archived=include_archived)
        if project is None:
            raise NotFoundError("Project not found")
        if not self.permissions.can_view_project(user, project):
            raise ForbiddenError("You do not have access to this project")
        return project

    def _get_for_manage(self, slug: str, user: User) -> Project:
        project = self.projects.get_by_slug(slug, include_archived=True)
        if project is None:
            raise NotFoundError("Project not found")
        if not self.permissions.can_manage_project(user, project):
            raise ForbiddenError("You cannot manage this project")
        return project

    def update(self, slug: str, data: ProjectUpdate, user: User) -> Project:
        project = self._get_for_manage(slug, user)
        fields = data.model_dump(exclude_unset=True)
        project = self.projects.update(project, **fields)
        self.db.commit()
        self.db.refresh(project)
        return project

    def soft_delete(self, slug: str, user: User) -> Project:
        project = self._get_for_manage(slug, user)
        if not project.is_archived:
            project = self.projects.update(project, is_archived=True)
            self.db.commit()
            self.db.refresh(project)
        return project

    def add_member(
        self, slug: str, data: ProjectMemberCreate, user: User
    ) -> ProjectMember:
        project = self._get_for_manage(slug, user)
        target = self.users.get_by_email(data.email)
        if target is None:
            raise NotFoundError("No user found with that email")
        if self.members.get(project.id, target.id) is not None:
            raise ConflictError("User is already a member of this project")
        member = self.members.add(
            project_id=project.id, user_id=target.id, role=data.role
        )
        self.db.commit()
        self.db.refresh(member)
        return member

    def list_members(self, slug: str, user: User) -> list[ProjectMember]:
        project = self.get(slug, user)
        return self.members.list_by_project(project.id)

    def update_member_role(
        self, slug: str, user_id: int, role: ProjectRole, user: User
    ) -> ProjectMember:
        project = self._get_for_manage(slug, user)
        member = self.members.get(project.id, user_id)
        if member is None:
            raise NotFoundError("Member not found")
        if project.owner_id == user_id:
            raise ConflictError("The project owner's role cannot be changed")
        member = self.members.update_role(member, role)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, slug: str, user_id: int, user: User) -> None:
        project = self._get_for_manage(slug, user)
        if project.owner_id == user_id:
            raise ForbiddenError("The project owner cannot be removed")
        member = self.members.get(project.id, user_id)
        if member is None:
            raise NotFoundError("User is not a member of this project")
        self.members.delete(member)
        self.db.commit()