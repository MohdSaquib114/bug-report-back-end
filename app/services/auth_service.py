from sqlalchemy.orm import Session

from app.models.api_tokens import ApiToken
from app.repositories.token_repository import TokenRepository
from app.security import generate_token
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.tokens = TokenRepository(db)
        self.users = UserService(db)

    def login(self, *, email: str, password: str) -> ApiToken:
        user = self.users.authenticate(email=email, password=password)
        api_token = self.tokens.create(
            user_id=user.id, token=generate_token(), expires_in_days=30
        )
        self.db.commit()
        self.db.refresh(api_token)
        return api_token

    def logout(self, token: str) -> None:
        self.tokens.revoke(token)
        self.db.commit()