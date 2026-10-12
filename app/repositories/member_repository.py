from sqlalchemy import select

from app.models.project_members import ProjectMember, ProjectRole
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository):
    def add(
        self, *, project_id: int, user_id: int, role: ProjectRole
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.flush()
        return member

    def get(self, project_id: int, user_id: int) -> ProjectMember | None:
        return self.db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )

    def list_by_project(self, project_id: int) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.id)
        )
        return list(self.db.scalars(stmt).all())

    def is_member(self, project_id: int, user_id: int) -> bool:
        return (
            self.db.scalar(
                select(ProjectMember.id).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
            is not None
        )

    def update_role(self, member: ProjectMember, role: ProjectRole) -> ProjectMember:
        member.role = role
        self.db.flush()
        return member