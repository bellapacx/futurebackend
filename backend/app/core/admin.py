from enum import IntEnum

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_client


class AdminRole(IntEnum):
    DEVELOPER = 1
    ADMIN = 2
    OWNER = 3


ROLE_NAME_BY_LEVEL = {
    AdminRole.DEVELOPER: "developer",
    AdminRole.ADMIN: "admin",
    AdminRole.OWNER: "owner",
}

ROLE_LEVEL_BY_NAME = {v: k for k, v in ROLE_NAME_BY_LEVEL.items()}


def get_admin_role(
    user: CurrentUser = Depends(get_current_user),
) -> tuple[CurrentUser, AdminRole]:
    """
    Resolves the caller's admin role from the admin_users table.
    Raises 403 if the user is not an admin at all.
    """
    client = get_service_client()
    rows = (
        client.table("admin_users")
        .select("role")
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    ).data or []

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    role_name = rows[0].get("role", "developer")
    role = ROLE_LEVEL_BY_NAME.get(role_name)
    if role is None:
        # Unknown role string — treat as lowest privilege
        role = AdminRole.DEVELOPER

    return user, role


def require_role(min_role: AdminRole):
    """
    Dependency factory. Usage:
        Depends(require_role(AdminRole.ADMIN))
    """

    def dep(
        user_role: tuple[CurrentUser, AdminRole] = Depends(get_admin_role),
    ) -> tuple[CurrentUser, AdminRole]:
        user, role = user_role
        if role < min_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {ROLE_NAME_BY_LEVEL[min_role]} role or higher",
            )
        return user, role

    return dep


# Convenience aliases so routers stay readable
require_admin_read = require_role(AdminRole.DEVELOPER)
require_admin_write = require_role(AdminRole.ADMIN)
require_admin_owner = require_role(AdminRole.OWNER)