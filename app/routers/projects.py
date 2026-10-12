from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.models.projects import Project
from app.models.users import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectMemberUpdate,
    ProjectOut,
    ProjectUpdate,
)
from app.services.project_service import ProjectService
from config.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    return ProjectService(db).create(user, data)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    include_archived: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Project]:
    return ProjectService(db).list(
        user, include_archived=include_archived, offset=offset, limit=limit
    )


@router.get("/{slug}", response_model=ProjectOut)
def get_project(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    return ProjectService(db).get(slug, user)


@router.patch("/{slug}", response_model=ProjectOut)
def update_project(
    slug: str,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    return ProjectService(db).update(slug, data, user)


@router.delete("/{slug}", response_model=ProjectOut)
def soft_delete_project(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Soft delete: marks the project as archived, data is retained."""
    return ProjectService(db).soft_delete(slug, user)


@router.get("/{slug}/members", response_model=list[ProjectMemberOut])
def list_members(
    slug: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ProjectService(db).list_members(slug, user)


@router.post(
    "/{slug}/members",
    response_model=ProjectMemberOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    slug: str,
    data: ProjectMemberCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ProjectService(db).add_member(slug, data, user)


@router.patch("/{slug}/members/{user_id}", response_model=ProjectMemberOut)
def update_member(
    slug: str,
    user_id: int,
    data: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ProjectService(db).update_member(slug, user_id, data.role, user)


@router.delete("/{slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    slug: str,
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    ProjectService(db).remove_member(slug, user_id, user)