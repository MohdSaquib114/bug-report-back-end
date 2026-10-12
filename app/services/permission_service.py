from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models.bugs import Bug
from app.models.permissions import Permission
from app.models.project_members import ProjectMember, ProjectRole
from app.models.projects import Project
from app.models.users import User, UserRole
from app.repositories.member_repository import MemberRepository
from app.repositories.permission_repository import PermissionRepository

_ROLE_RANK = {
    ProjectRole.VIEWER: 1,
    ProjectRole.CONTRIBUTOR: 2,
    ProjectRole.MAINTAINER: 3,
    ProjectRole.OWNER: 4,
}


class PermissionService:
    """Central place for project/bug authorization rules."""

    def __init__(self, db: Session):
        self.db = db
        self.members = MemberRepository(db)
        self.permissions = PermissionRepository(db)

    def is_admin(self, user: User) -> bool:
        return user.role == UserRole.ADMIN

    def is_owner(self, user: User, project: Project) -> bool:
        return project.owner_id == user.id

    def member(self, project_id: int, user_id: int) -> ProjectMember | None:
        return self.members.get(project_id, user_id)

    def has_permission(self, user: User, name: str) -> bool:
        if self.is_admin(user):
            return True
        return self.permissions.user_has_permission(user.id, name)

    @staticmethod
    def _rank(member: ProjectMember | None) -> int:
        return _ROLE_RANK.get(member.role, 0) if member else 0

    def can_view_project(self, user: User, project: Project) -> bool:
        if self.is_admin(user) or self.is_owner(user, project):
            return True
        if self.members.is_member(project.id, user.id):
            return True
        return self.permissions.user_has_permission(user.id, "bug.view")

    def can_manage_project(self, user: User, project: Project) -> bool:
        if self.is_admin(user) or self.is_owner(user, project):
            return True
        return self.permissions.user_has_permission(user.id, "project.manage")

    def can_view_bug(self, user: User, bug: Bug) -> bool:
        if self.is_admin(user):
            return True
        member = self.member(bug.project_id, user.id)
        if self._rank(member) >= _ROLE_RANK[ProjectRole.VIEWER]:
            return True
        if self.is_owner(user, bug.project):
            return True
        return self.permissions.user_has_permission(user.id, "bug.view")

    def can_create_bug(self, user: User, project: Project) -> bool:
        if self.is_admin(user) or self.is_owner(user, project):
            return True
        member = self.member(project.id, user.id)
        if self._rank(member) >= _ROLE_RANK[ProjectRole.CONTRIBUTOR]:
            return True
        return self.permissions.user_has_permission(user.id, "bug.create")

    def can_update_bug(self, user: User, bug: Bug) -> bool:
        if self.is_admin(user) or self.is_owner(user, bug.project):
            return True
        member = self.member(bug.project_id, user.id)
        if self._rank(member) >= _ROLE_RANK[ProjectRole.MAINTAINER]:
            return True
        return self.permissions.user_has_permission(user.id, "bug.update")

    def can_delete_bug(self, user: User, bug: Bug) -> bool:
        if self.is_admin(user) or self.is_owner(user, bug.project):
            return True
        return self.permissions.user_has_permission(user.id, "bug.delete")

    # ------------------------------------------------------------------
    # Permission administration
    # ------------------------------------------------------------------
    def grant(self, user: User, permission_name: str) -> Permission:
        permission = self.permissions.get_by_name(permission_name)
        if permission is None:
            raise NotFoundError("Unknown permission: {0}".format(permission_name))
        self.permissions.grant_to_user(user.id, permission)
        self.db.commit()
        return permission

    def names_for_user(self, user: User) -> list[str]:
        return self.permissions.user_permission_names(user.id)