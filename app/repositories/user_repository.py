from sqlalchemy import select

from app.models.users import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def list(self, *, offset: int = 0, limit: int = 50) -> list[User]:
        stmt = select(User).order_by(User.id).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.flush()
        return user