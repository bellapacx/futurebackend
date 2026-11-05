from fastapi import APIRouter, Body, Depends, Query

from app.core.admin import (
    AdminRole,
    ROLE_NAME_BY_LEVEL,
    require_admin_owner,
    require_admin_read,
    require_admin_write,
)
from app.core.auth import CurrentUser
from app.core.db import get_service_client, with_db_retry
from app.modules.admin import service
from app.modules.admin.schemas import (
    AdminCreateRequest,
    AdminListItem,
    AdminUpdateRequest,
    AdminsListResponse,
    AuditLogItem,
    AuditLogListResponse,
    EntitlementsListResponse,
    EntitlementUpdateRequest,
    IndicatorVersionListItem,
    IndicatorVersionsListResponse,
    OverviewResponse,
    UserDetailResponse,
    UserListItem,
    UsersListResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ----------------------------------------------------------------------
# Overview
# ----------------------------------------------------------------------

@router.get("/overview", response_model=OverviewResponse)
@with_db_retry
def overview(
    user_role: tuple[CurrentUser, AdminRole] = Depends(require_admin_read),
) -> OverviewResponse:
    user, role = user_role
    client = get_service_client()

    users = client.table("profiles").select("id", count="exact").execute()
    ents = (
        client.table("user_entitlements")
        .select("user_id", count="exact")
        .eq("is_active", True)
        .execute()
    )
    inds = (
        client.table("indicator_versions")
        .select("id", count="exact")
        .eq("status", "active")
        .execute()
    )

    return OverviewResponse(
        total_users=users.count or 0,
        active_entitlements=ents.count or 0,
        active_indicator_versions=inds.count or 0,
        admin_user_id=user.user_id,
        admin_role=ROLE_NAME_BY_LEVEL[role],
    )


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

@router.get("/users", response_model=UsersListResponse)
@with_db_retry
def list_users(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _=Depends(require_admin_read),
) -> UsersListResponse:
    rows, total = service.list_users(q=q, limit=limit, offset=offset)
    return UsersListResponse(
        items=[UserListItem(**r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
@with_db_retry
def get_user(
    user_id: str,
    _=Depends(require_admin_read),
) -> UserDetailResponse:
    return UserDetailResponse(**service.get_user_detail(user_id))


@router.patch("/users/{user_id}/entitlement", response_model=UserDetailResponse)
def patch_entitlement(
    user_id: str,
    payload: EntitlementUpdateRequest,
    body: dict = Body(...),   # need raw body to detect explicit null for expires_at
    user_role: tuple[CurrentUser, AdminRole] = Depends(require_admin_write),
) -> UserDetailResponse:
    user, role = user_role
    expires_at_set = "expires_at" in body
    service.update_user_entitlement(
        admin_user_id=user.user_id,
        admin_role=role,
        user_id=user_id,
        is_active=payload.is_active,
        plan_tier=payload.plan_tier,
        expires_at=payload.expires_at,
        expires_at_set=expires_at_set,
    )
    return UserDetailResponse(**service.get_user_detail(user_id))


# ----------------------------------------------------------------------
# Entitlements
# ----------------------------------------------------------------------

@router.get("/entitlements", response_model=EntitlementsListResponse)
@with_db_retry
def list_entitlements(
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _=Depends(require_admin_read),
) -> EntitlementsListResponse:
    rows, total = service.list_entitlements(
        is_active=is_active, limit=limit, offset=offset
    )
    return EntitlementsListResponse(
        items=rows, total=total, limit=limit, offset=offset
    )


# ----------------------------------------------------------------------
# Indicator versions
# ----------------------------------------------------------------------

@router.get("/indicator-versions", response_model=IndicatorVersionsListResponse)
@with_db_retry
def list_indicator_versions(
    _=Depends(require_admin_read),
) -> IndicatorVersionsListResponse:
    rows = service.list_indicator_versions()
    return IndicatorVersionsListResponse(
        items=[IndicatorVersionListItem(**r) for r in rows],
        total=len(rows),
    )


# ----------------------------------------------------------------------
# Admin roster (owner only)
# ----------------------------------------------------------------------

@router.get("/admins", response_model=AdminsListResponse)
@with_db_retry
def list_admins(
    _=Depends(require_admin_owner),
) -> AdminsListResponse:
    rows = service.list_admins()
    return AdminsListResponse(items=[AdminListItem(**r) for r in rows])


@router.post("/admins", response_model=AdminListItem)
@with_db_retry
def create_admin(
    payload: AdminCreateRequest,
    user_role: tuple[CurrentUser, AdminRole] = Depends(require_admin_owner),
) -> AdminListItem:
    user, role = user_role
    created = service.create_admin(
        admin_user_id=user.user_id,
        admin_role=role,
        email=payload.email,
        role=payload.role,
    )
    # Fetch the full row so the response matches the list shape
    rows = service.list_admins()
    match = next((r for r in rows if r["user_id"] == created["user_id"]), None)
    return AdminListItem(**match)


@router.patch("/admins/{target_user_id}", response_model=AdminListItem)
@with_db_retry
def update_admin(
    target_user_id: str,
    payload: AdminUpdateRequest,
    user_role: tuple[CurrentUser, AdminRole] = Depends(require_admin_owner),
) -> AdminListItem:
    user, role = user_role
    service.update_admin_role(
        admin_user_id=user.user_id,
        admin_role=role,
        target_user_id=target_user_id,
        new_role=payload.role,
    )
    rows = service.list_admins()
    match = next((r for r in rows if r["user_id"] == target_user_id), None)
    return AdminListItem(**match)


@router.delete("/admins/{target_user_id}")
@with_db_retry
def delete_admin(
    target_user_id: str,
    user_role: tuple[CurrentUser, AdminRole] = Depends(require_admin_owner),
) -> dict:
    user, role = user_role
    return service.delete_admin(
        admin_user_id=user.user_id,
        admin_role=role,
        target_user_id=target_user_id,
    )


# ----------------------------------------------------------------------
# Audit log (readable by all admin tiers)
# ----------------------------------------------------------------------

@router.get("/audit-log", response_model=AuditLogListResponse)
@with_db_retry
def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _=Depends(require_admin_read),
) -> AuditLogListResponse:
    rows, total = service.list_audit_log(limit=limit, offset=offset)
    return AuditLogListResponse(
        items=[AuditLogItem(**r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )