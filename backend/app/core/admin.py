from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_client


def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    client = get_service_client()
    result = (
        client.table("admin_users")
        .select("role")
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user