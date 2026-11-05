from fastapi import APIRouter, Depends

from app.auth import CurrentUser
from app.core.admin import require_admin
from app.core.db import get_service_client

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def overview(user: CurrentUser = Depends(require_admin)) -> dict:
    client = get_service_client()

    users = client.table("profiles").select("id", count="exact").execute()
    entitlements_active = (
        client.table("user_entitlements")
        .select("*", count="exact")
        .eq("is_active", True)
        .execute()
    )
    indicators = (
        client.table("indicator_versions")
        .select("*", count="exact")
        .eq("status", "active")
        .execute()
    )

    return {
        "total_users": users.count or 0,
        "active_entitlements": entitlements_active.count or 0,
        "active_indicator_versions": indicators.count or 0,
        "admin_user_id": user.user_id,
    }