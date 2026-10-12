from datetime import datetime, timezone

from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseRepository:
    """Thin wrapper that gives each repository a database session."""

    def __init__(self, db: Session):
        self.db = db

    def add(self, instance):
        self.db.add(instance)
        return instance

    def delete(self, instance) -> None:
        self.db.delete(instance)

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, instance) -> None:
        self.db.refresh(instance)

    def commit(self) -> None:
        self.db.commit()