from enum import Enum as pyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from config.database import Base


class StatusEnum(pyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BugPriority(pyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Bug(Base):
    __tablename__ = "bugs"
    __table_args__ = (
        Index("ix_bugs_project_status", "project_id", "status"),
        Index("ix_bugs_project_priority", "project_id", "priority"),
        Index("ix_bugs_assignee_status", "assignee_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(StatusEnum, name="bug_status", values_callable=lambda e: [m.value for m in e]),
        default=StatusEnum.OPEN,
        nullable=False,
        index=True,
    )
    priority = Column(
        Enum(
            BugPriority,
            name="bug_priority",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=BugPriority.MEDIUM,
        nullable=False,
    )
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reporter_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assignee_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_address = Column(String, nullable=True)
    location = Column(String, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="bugs")
    reporter = relationship(
        "User", back_populates="reported_bugs", foreign_keys=[reporter_id]
    )
    assignee = relationship(
        "User", back_populates="assigned_bugs", foreign_keys=[assignee_id]
    )
    attachments = relationship("Attachment", back_populates="bug", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="bug", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="bug", cascade="all, delete-orphan")
