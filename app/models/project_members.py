from enum import Enum as pyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship

from config.database import Base


class ProjectRole(pyEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(
        Enum(
            ProjectRole,
            name="project_role",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ProjectRole.CONTRIBUTOR,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")