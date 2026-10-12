from sqlalchemy.orm import Session

from app.errors import ConflictError, UnauthorizedError
from app.models.users import User, UserRole
from app.repositories.user_repository import UserRepository
from app.security import hash_password, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        if self.users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists")

        user = self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("This account is inactive")
        return user

    def get(self, user_id: int) -> User | None:
        return self.users.get_by_id(user_id)

    def list(self, *, offset: int = 0, limit: int = 50) -> list[User]:
        return self.users.list(offset=offset, limit=limit)