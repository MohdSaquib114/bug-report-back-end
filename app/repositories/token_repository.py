from datetime import timedelta

from sqlalchemy import delete, select, update

from app.models.api_tokens import ApiToken
from app.models.users import User
from app.repositories.base import BaseRepository, utcnow


class TokenRepository(BaseRepository):
    def create(
        self, *, user_id: int, token: str, expires_in_days: int | None = None
    ) -> ApiToken:
        expires_at = (
            utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        )
        api_token = ApiToken(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(api_token)
        self.db.flush()
        return api_token

    def get_user_by_token(self, token: str) -> User | None:
        row = self.db.execute(
            select(ApiToken, User)
            .join(User, User.id == ApiToken.user_id)
            .where(ApiToken.token == token, ApiToken.is_active.is_(True))
        ).first()
        if row is None:
            return None

        api_token, user = row
        now = utcnow()
        if api_token.expires_at is not None:
            expires_at = api_token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=now.tzinfo)
            if expires_at < now:
                return None

        api_token.last_used_at = now
        self.db.flush()
        return user

    def revoke(self, token: str) -> None:
        self.db.execute(
            update(ApiToken).where(ApiToken.token == token).values(is_active=False)
        )

    def delete_for_user(self, user_id: int) -> None:
        self.db.execute(delete(ApiToken).where(ApiToken.user_id == user_id))