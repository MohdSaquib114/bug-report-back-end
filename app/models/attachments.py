from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from config.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    url = Column(String, nullable=False)
    storage_key = Column(String, nullable=True, index=True)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    bug_id = Column(
        Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bug = relationship("Bug", back_populates="attachments")
    uploaded_by = relationship("User", back_populates="uploaded_attachments")
