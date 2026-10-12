from enum import Enum as pyEnum

from sqlalchemy import Column, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import relationship

from config.database import Base


class Actions(pyEnum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    ALL = "all"


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    action = Column(
        Enum(Actions, name="permission_action", values_callable=lambda e: [m.value for m in e]),
        default=Actions.VIEW,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users = relationship("User", secondary="user_permissions", back_populates="permissions")
