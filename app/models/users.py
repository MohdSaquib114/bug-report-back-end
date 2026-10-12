from enum import Enum as pyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import relationship

from config.database import Base


class UserRole(pyEnum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owned_projects = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    project_memberships = relationship(
        "ProjectMember", back_populates="user", cascade="all, delete-orphan"
    )
    reported_bugs = relationship(
        "Bug", back_populates="reporter", foreign_keys="Bug.reporter_id"
    )
    assigned_bugs = relationship(
        "Bug", back_populates="assignee", foreign_keys="Bug.assignee_id"
    )
    comments = relationship("Comment", back_populates="author")
    activities = relationship("ActivityLog", back_populates="actor")
    uploaded_attachments = relationship("Attachment", back_populates="uploaded_by")
    tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship(
        "Permission", secondary="user_permissions", back_populates="users"
    )
