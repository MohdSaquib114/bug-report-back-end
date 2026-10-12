from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, func

from config.database import Base

user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("granted_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
