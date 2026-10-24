from pydantic import BaseModel


class EntitlementSummary(BaseModel):
    is_active: bool
    plan_tier: str | None = None
    expires_at: str | None = None


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    role: str | None
    entitlement: EntitlementSummary | None


class ProfileResponse(BaseModel):
    user_id: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    auth_provider: str | None
    created_at: str | None


class ProfileUpdateRequest(BaseModel):
    display_name: str