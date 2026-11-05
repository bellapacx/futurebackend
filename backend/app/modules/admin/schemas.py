from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

AdminRoleLiteral = Literal["owner", "admin", "developer"]


# ---- Overview ------------------------------------------------------------

class OverviewResponse(BaseModel):
    total_users: int
    active_entitlements: int
    active_indicator_versions: int
    admin_user_id: str
    admin_role: AdminRoleLiteral


# ---- Users ---------------------------------------------------------------

class UserListItem(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    created_at: datetime | None
    entitlement_active: bool
    entitlement_plan_tier: str | None
    entitlement_expires_at: datetime | None


class UsersListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    limit: int
    offset: int


class UserDetailResponse(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    auth_provider: str | None
    created_at: datetime | None
    entitlement: dict[str, Any] | None   # raw user_entitlements row


# ---- Entitlements --------------------------------------------------------

class EntitlementItem(BaseModel):
    user_id: str
    membership_id: str | None
    is_active: bool
    plan_tier: str | None
    expires_at: datetime | None
    last_verified_at: datetime | None
    updated_at: datetime
    email: str | None = None
    display_name: str | None = None


class EntitlementsListResponse(BaseModel):
    items: list[EntitlementItem]
    total: int
    limit: int
    offset: int


class EntitlementUpdateRequest(BaseModel):
    is_active: bool | None = None
    plan_tier: str | None = None
    expires_at: datetime | None = None   # explicit null = "never expires"


# ---- Indicator versions --------------------------------------------------

class IndicatorVersionListItem(BaseModel):
    id: str
    version_label: str
    status: str
    source_hash: str | None
    validated_at: datetime | None
    activated_at: datetime | None
    activated_by: str | None
    created_at: datetime
    created_by: str | None
    notes: str | None
    has_source: bool   # True if pine_source_encrypted is present; never leak the bytes


class IndicatorVersionsListResponse(BaseModel):
    items: list[IndicatorVersionListItem]
    total: int


# ---- Admins roster -------------------------------------------------------

class AdminListItem(BaseModel):
    user_id: str
    role: AdminRoleLiteral
    email: str | None = None
    display_name: str | None = None
    created_at: datetime


class AdminsListResponse(BaseModel):
    items: list[AdminListItem]


class AdminCreateRequest(BaseModel):
    email: EmailStr
    role: AdminRoleLiteral


class AdminUpdateRequest(BaseModel):
    role: AdminRoleLiteral


# ---- Audit log -----------------------------------------------------------

class AuditLogItem(BaseModel):
    id: str
    admin_user_id: str
    admin_role: str
    action: str
    target_user_id: str | None
    target_table: str | None
    target_id: str | None
    payload: dict[str, Any] | None
    created_at: datetime
    admin_email: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    limit: int
    offset: int