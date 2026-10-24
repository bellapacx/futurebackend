from datetime import datetime, timezone

from app.core.db import get_service_client


def _is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return exp < datetime.now(timezone.utc)


def is_entitled(user_id: str) -> bool:
    client = get_service_client()
    result = (
        client.table("user_entitlements")
        .select("is_active, expires_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return False
    row = rows[0]
    if not row.get("is_active"):
        return False
    return not _is_expired(row.get("expires_at"))


def get_entitlement(user_id: str) -> dict | None:
    client = get_service_client()
    result = (
        client.table("user_entitlements")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None