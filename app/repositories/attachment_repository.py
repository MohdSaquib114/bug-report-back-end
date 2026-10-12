from sqlalchemy import select

from app.models.attachments import Attachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository):
    def create(
        self,
        *,
        bug_id: int,
        url: str,
        storage_key: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
        uploaded_by_id: int | None = None,
    ) -> Attachment:
        attachment = Attachment(
            bug_id=bug_id,
            url=url,
            storage_key=storage_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_by_id=uploaded_by_id,
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def list_by_bug(self, bug_id: int) -> list:
        stmt = (
            select(Attachment)
            .where(Attachment.bug_id == bug_id)
            .order_by(Attachment.id)
        )
        return list(self.db.scalars(stmt).all())