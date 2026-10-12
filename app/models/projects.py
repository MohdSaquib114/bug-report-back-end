from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from config.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=True)
    description = Column(String, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="owned_projects")
    bugs = relationship("Bug", back_populates="project", cascade="all, delete-orphan")
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
