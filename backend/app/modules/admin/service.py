from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.admin import AdminRole, ROLE_NAME_BY_LEVEL
from app.core.db import get_service_client
from app.core.errors import NotFoundError


# ----------------------------------------------------------------------
# Audit
# ----------------------------------------------------------------------

def log_audit(
    *,
    admin_user_id: str,
    admin_role: AdminRole,
    action: str,
    target_user_id: str | None = None,
    target_table: str | None = None,
    target_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    client = get_service_client()
    client.table("admin_audit_log").insert(
        {
            "admin_user_id": admin_user_id,
            "admin_role": ROLE_NAME_BY_LEVEL[admin_role],
            "action": action,
            "target_user_id": target_user_id,
            "target_table": target_table,
            "target_id": target_id,
            "payload": payload,
        }
    ).execute()


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

def list_users(
    q: str | None, limit: int, offset: int
) -> tuple[list[dict], int]:
    """Returns (rows, total). Joins profiles + user_entitlements in Python."""
    client = get_service_client()

    query = client.table("profiles").select(
        "id, email, display_name, created_at",
        count="exact",
    )
    if q:
        # Supabase .or_ uses PostgREST syntax
        query = query.or_(f"email.ilike.%{q}%,display_name.ilike.%{q}%")

    resp = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    profiles = resp.data or []
    total = resp.count or 0

    user_ids = [p["id"] for p in profiles]
    ent_by_user: dict[str, dict] = {}
    if user_ids:
        ents = (
            client.table("user_entitlements")
            .select("user_id, is_active, plan_tier, expires_at")
            .in_("user_id", user_ids)
            .execute()
        ).data or []
        ent_by_user = {e["user_id"]: e for e in ents}

    merged = []
    for p in profiles:
        e = ent_by_user.get(p["id"], {})
        merged.append(
            {
                "user_id": p["id"],
                "email": p.get("email"),
                "display_name": p.get("display_name"),
                "created_at": p.get("created_at"),
                "entitlement_active": bool(e.get("is_active")),
                "entitlement_plan_tier": e.get("plan_tier"),
                "entitlement_expires_at": e.get("expires_at"),
            }
        )
    return merged, total


def get_user_detail(user_id: str) -> dict:
    client = get_service_client()

    profile_rows = (
        client.table("profiles")
        .select("id, email, display_name, avatar_url, auth_provider, created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
    ).data or []
    if not profile_rows:
        raise NotFoundError("User not found")

    p = profile_rows[0]
    ent_rows = (
        client.table("user_entitlements")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    ).data or []

    return {
        "user_id": p["id"],
        "email": p.get("email"),
        "display_name": p.get("display_name"),
        "avatar_url": p.get("avatar_url"),
        "auth_provider": p.get("auth_provider"),
        "created_at": p.get("created_at"),
        "entitlement": ent_rows[0] if ent_rows else None,
    }


def update_user_entitlement(
    *,
    admin_user_id: str,
    admin_role: AdminRole,
    user_id: str,
    is_active: bool | None,
    plan_tier: str | None,
    expires_at: datetime | None,
    expires_at_set: bool,
) -> dict:
    client = get_service_client()

    existing_rows = (
        client.table("user_entitlements")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    ).data or []

    update: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if is_active is not None:
        update["is_active"] = is_active
    if plan_tier is not None:
        update["plan_tier"] = plan_tier
    if expires_at_set:
        update["expires_at"] = expires_at.isoformat() if expires_at else None

    before = existing_rows[0] if existing_rows else None

    if existing_rows:
        client.table("user_entitlements").update(update).eq(
            "user_id", user_id
        ).execute()
    else:
        insert_row = {"user_id": user_id, **update}
        insert_row.setdefault("is_active", False)
        client.table("user_entitlements").insert(insert_row).execute()

    after_rows = (
        client.table("user_entitlements")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    ).data or []

    log_audit(
        admin_user_id=admin_user_id,
        admin_role=admin_role,
        action="entitlement.update",
        target_user_id=user_id,
        target_table="user_entitlements",
        target_id=None,
        payload={"before": before, "after": after_rows[0] if after_rows else None},
    )
    return after_rows[0] if after_rows else {}


# ----------------------------------------------------------------------
# Entitlements
# ----------------------------------------------------------------------

def list_entitlements(
    is_active: bool | None, limit: int, offset: int
) -> tuple[list[dict], int]:
    client = get_service_client()
    query = client.table("user_entitlements").select("*", count="exact")
    if is_active is not None:
        query = query.eq("is_active", is_active)

    resp = (
        query.order("updated_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    rows = resp.data or []
    total = resp.count or 0

    user_ids = [r["user_id"] for r in rows]
    profiles_by_id: dict[str, dict] = {}
    if user_ids:
        profiles = (
            client.table("profiles")
            .select("id, email, display_name")
            .in_("id", user_ids)
            .execute()
        ).data or []
        profiles_by_id = {p["id"]: p for p in profiles}

    for r in rows:
        p = profiles_by_id.get(r["user_id"], {})
        r["email"] = p.get("email")
        r["display_name"] = p.get("display_name")

    return rows, total


# ----------------------------------------------------------------------
# Indicator versions
# ----------------------------------------------------------------------

def list_indicator_versions() -> list[dict]:
    client = get_service_client()
    rows = (
        client.table("indicator_versions")
        .select(
            "id, version_label, status, source_hash, validated_at, "
            "activated_at, activated_by, created_at, created_by, notes, "
            "pine_source_encrypted"
        )
        .order("created_at", desc=True)
        .execute()
    ).data or []

    # Never leak the encrypted source to the client
    out = []
    for r in rows:
        has_source = r.pop("pine_source_encrypted", None) is not None
        r["has_source"] = has_source
        out.append(r)
    return out


# ----------------------------------------------------------------------
# Admin roster
# ----------------------------------------------------------------------

def list_admins() -> list[dict]:
    client = get_service_client()
    rows = (
        client.table("admin_users")
        .select("user_id, role, created_at")
        .order("created_at")
        .execute()
    ).data or []

    user_ids = [r["user_id"] for r in rows]
    profiles_by_id: dict[str, dict] = {}
    if user_ids:
        profiles = (
            client.table("profiles")
            .select("id, email, display_name")
            .in_("id", user_ids)
            .execute()
        ).data or []
        profiles_by_id = {p["id"]: p for p in profiles}

    for r in rows:
        p = profiles_by_id.get(r["user_id"], {})
        r["email"] = p.get("email")
        r["display_name"] = p.get("display_name")
    return rows


def create_admin(
    *,
    admin_user_id: str,
    admin_role: AdminRole,
    email: str,
    role: str,
) -> dict:
    client = get_service_client()

    # Look up user by email in profiles
    rows = (
        client.table("profiles").select("id, email").eq("email", email).limit(1).execute()
    ).data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user with that email — they must sign in once first",
        )
    target_user_id = rows[0]["id"]

    # Prevent duplicate
    dup = (
        client.table("admin_users")
        .select("user_id")
        .eq("user_id", target_user_id)
        .limit(1)
        .execute()
    ).data or []
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an admin",
        )

    client.table("admin_users").insert(
        {"user_id": target_user_id, "role": role}
    ).execute()

    log_audit(
        admin_user_id=admin_user_id,
        admin_role=admin_role,
        action="admin.create",
        target_user_id=target_user_id,
        target_table="admin_users",
        payload={"email": email, "role": role},
    )

    return {"user_id": target_user_id, "role": role, "email": email}


def update_admin_role(
    *,
    admin_user_id: str,
    admin_role: AdminRole,
    target_user_id: str,
    new_role: str,
) -> dict:
    client = get_service_client()

    current = (
        client.table("admin_users")
        .select("user_id, role")
        .eq("user_id", target_user_id)
        .limit(1)
        .execute()
    ).data or []
    if not current:
        raise NotFoundError("Admin not found")

    old_role = current[0]["role"]

    # Owner cannot demote themselves
    if target_user_id == admin_user_id and old_role == "owner" and new_role != "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot demote themselves",
        )

    # Can't promote someone to owner if an owner already exists (single-owner invariant)
    if new_role == "owner" and old_role != "owner":
        existing_owner = (
            client.table("admin_users")
            .select("user_id")
            .eq("role", "owner")
            .limit(1)
            .execute()
        ).data or []
        if existing_owner:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An owner already exists. Transfer ownership first.",
            )

    client.table("admin_users").update({"role": new_role}).eq(
        "user_id", target_user_id
    ).execute()

    log_audit(
        admin_user_id=admin_user_id,
        admin_role=admin_role,
        action="admin.update_role",
        target_user_id=target_user_id,
        target_table="admin_users",
        payload={"from": old_role, "to": new_role},
    )
    return {"user_id": target_user_id, "role": new_role}


def delete_admin(
    *, admin_user_id: str, admin_role: AdminRole, target_user_id: str
) -> dict:
    client = get_service_client()

    if target_user_id == admin_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself",
        )

    current = (
        client.table("admin_users")
        .select("user_id, role")
        .eq("user_id", target_user_id)
        .limit(1)
        .execute()
    ).data or []
    if not current:
        raise NotFoundError("Admin not found")

    if current[0]["role"] == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner. Transfer ownership first.",
        )

    client.table("admin_users").delete().eq("user_id", target_user_id).execute()

    log_audit(
        admin_user_id=admin_user_id,
        admin_role=admin_role,
        action="admin.delete",
        target_user_id=target_user_id,
        target_table="admin_users",
    )
    return {"deleted": True, "user_id": target_user_id}


# ----------------------------------------------------------------------
# Audit log read
# ----------------------------------------------------------------------

def list_audit_log(limit: int, offset: int) -> tuple[list[dict], int]:
    client = get_service_client()
    resp = (
        client.table("admin_audit_log")
        .select("*", count="exact")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    rows = resp.data or []
    total = resp.count or 0

    admin_ids = list({r["admin_user_id"] for r in rows})
    profiles_by_id: dict[str, dict] = {}
    if admin_ids:
        profiles = (
            client.table("profiles")
            .select("id, email")
            .in_("id", admin_ids)
            .execute()
        ).data or []
        profiles_by_id = {p["id"]: p for p in profiles}

    for r in rows:
        r["admin_email"] = profiles_by_id.get(r["admin_user_id"], {}).get("email")
    return rows, total