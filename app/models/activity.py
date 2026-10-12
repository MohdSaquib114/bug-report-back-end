from enum import Enum as pyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from config.database import Base


class ActivityType(pyEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    COMMENTED = "commented"
    ATTACHMENT_ADDED = "attachment_added"


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_bug_created", "bug_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    bug_id = Column(
        Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activity_type = Column(
        Enum(
            ActivityType,
            name="activity_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bug = relationship("Bug", back_populates="activities")
    actor = relationship("User", back_populates="activities")