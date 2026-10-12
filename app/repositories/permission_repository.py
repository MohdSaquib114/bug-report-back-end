from sqlalchemy import select

from app.models.permissions import Actions, Permission
from app.models.user_permissions import user_permissions
from app.repositories.base import BaseRepository

DEFAULT_PERMISSIONS: dict[str, Actions] = {
    "bug.view": Actions.VIEW,
    "bug.create": Actions.CREATE,
    "bug.update": Actions.UPDATE,
    "bug.delete": Actions.DELETE,
    "project.manage": Actions.MANAGE,
    "user.manage": Actions.MANAGE,
}


class PermissionRepository(BaseRepository):
    def get_by_name(self, name: str) -> Permission | None:
        return self.db.scalar(select(Permission).where(Permission.name == name))

    def user_has_permission(self, user_id: int, permission_name: str) -> bool:
        stmt = (
            select(Permission.id)
            .join(
                user_permissions,
                user_permissions.c.permission_id == Permission.id,
            )
            .where(
                user_permissions.c.user_id == user_id,
                Permission.name == permission_name,
            )
        )
        return self.db.scalar(stmt) is not None

    def user_permission_names(self, user_id: int) -> list[str]:
        stmt = (
            select(Permission.name)
            .join(
                user_permissions,
                user_permissions.c.permission_id == Permission.id,
            )
            .where(user_permissions.c.user_id == user_id)
            .order_by(Permission.name)
        )
        return list(self.db.scalars(stmt).all())

    def grant_to_user(self, user_id: int, permission: Permission) -> bool:
        existing = self.db.execute(
            user_permissions.select().where(
                user_permissions.c.user_id == user_id,
                user_permissions.c.permission_id == permission.id,
            )
        ).first()
        if existing is not None:
            return False
        self.db.execute(
            user_permissions.insert().values(
                user_id=user_id, permission_id=permission.id
            )
        )
        self.db.flush()
        return True

    def seed_defaults(self) -> None:
        created = False
        for name, action in DEFAULT_PERMISSIONS.items():
            if self.get_by_name(name) is None:
                self.db.add(Permission(name=name, action=action))
                created = True
        if created:
            self.db.flush()