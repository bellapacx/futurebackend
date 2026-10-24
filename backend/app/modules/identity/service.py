from app.core.db import get_service_client


def get_entitlement_row(user_id: str) -> dict | None:
    client = get_service_client()
    result = (
        client.table("user_entitlements")
        .select("is_active, plan_tier, expires_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_profile_row(user_id: str) -> dict | None:
    client = get_service_client()
    result = (
        client.table("profiles")
        .select("id, email, display_name, avatar_url, auth_provider, created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def update_profile_display_name(user_id: str, display_name: str) -> dict | None:
    client = get_service_client()
    client.table("profiles").update(
        {"display_name": display_name}
    ).eq("id", user_id).execute()
    return get_profile_row(user_id)