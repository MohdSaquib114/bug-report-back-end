from sqlalchemy import select

from app.models.activity import ActivityLog, ActivityType
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository):
    def create(
        self,
        *,
        bug_id: int,
        activity_type: ActivityType,
        actor_id: int | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ActivityLog:
        activity = ActivityLog(
            bug_id=bug_id,
            actor_id=actor_id,
            activity_type=activity_type,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(activity)
        self.db.flush()
        return activity

    def list_by_bug(self, bug_id: int) -> list:
        stmt = (
            select(ActivityLog)
            .where(ActivityLog.bug_id == bug_id)
            .order_by(ActivityLog.created_at)
        )
        return list(self.db.scalars(stmt).all())