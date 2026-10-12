from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_bearer_token, get_current_user, require_admin
from app.errors import NotFoundError
from app.models.users import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.user_service import UserService
from config.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> User:
    return UserService(db).register(
        email=data.email, password=data.password, full_name=data.full_name
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)) -> Token:
    api_token = AuthService(db).login(email=data.email, password=data.password)
    return Token(access_token=api_token.token, expires_at=api_token.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(get_bearer_token), db: Session = Depends(get_db)) -> None:
    AuthService(db).logout(token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/me/permissions", response_model=list[str])
def my_permissions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[str]:
    return PermissionService(db).names_for_user(user)


@router.get("", response_model=list[UserOut])
def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    return UserService(db).list(offset=offset, limit=limit)


@router.post(
    "/{user_id}/permissions",
    response_model=list[str],
    status_code=status.HTTP_201_CREATED,
)
def grant_permission(
    user_id: int,
    permission: str = Query(..., description="Permission name, e.g. bug.view"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[str]:
    service = PermissionService(db)
    target = UserService(db).get(user_id)
    if target is None:
        raise NotFoundError("User not found")
    service.grant(target, permission)
    return service.names_for_user(target)