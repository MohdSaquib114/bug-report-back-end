from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from config.database import Base


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_bug_created", "bug_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    body = Column(Text, nullable=False)
    bug_id = Column(
        Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parent_id = Column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    is_edited = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bug = relationship("Bug", back_populates="comments")
    author = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
