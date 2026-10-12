from sqlalchemy import select

from app.models.comments import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository):
    def create(
        self,
        *,
        bug_id: int,
        body: str,
        author_id: int | None = None,
        parent_id: int | None = None,
    ) -> Comment:
        comment = Comment(
            bug_id=bug_id, body=body, author_id=author_id, parent_id=parent_id
        )
        self.db.add(comment)
        self.db.flush()
        return comment

    def get_by_id(self, comment_id: int) -> Comment | None:
        return self.db.get(Comment, comment_id)

    def list_by_bug(self, bug_id: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.bug_id == bug_id)
            .order_by(Comment.created_at)
        )
        return list(self.db.scalars(stmt).all())