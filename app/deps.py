from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.errors import ForbiddenError, UnauthorizedError
from app.models.users import User, UserRole
from app.repositories.token_repository import TokenRepository
from config.database import get_db


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Invalid authorization header")
    return token.strip()


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    token = _parse_bearer(authorization)
    if token is None:
        raise UnauthorizedError("Missing bearer token")
    return token


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_bearer_token),
) -> User:
    user = TokenRepository(db).get_user_by_token(token)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")
    if not user.is_active:
        raise UnauthorizedError("This account is inactive")
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User | None:
    try:
        token = _parse_bearer(authorization)
    except UnauthorizedError:
        return None
    if token is None:
        return None
    user = TokenRepository(db).get_user_by_token(token)
    if user is None or not user.is_active:
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return user