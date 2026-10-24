from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.modules.identity.schemas import (
    EntitlementSummary,
    MeResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.modules.identity.service import (
    get_entitlement_row,
    get_profile_row,
    update_profile_display_name,
)

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user)) -> MeResponse:
    row = get_entitlement_row(user.user_id)
    ent = None
    if row:
        ent = EntitlementSummary(
            is_active=bool(row.get("is_active")),
            plan_tier=row.get("plan_tier"),
            expires_at=row.get("expires_at"),
        )
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        entitlement=ent,
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(user: CurrentUser = Depends(get_current_user)) -> ProfileResponse:
    row = get_profile_row(user.user_id)
    if not row:
        return ProfileResponse(
            user_id=user.user_id,
            email=user.email,
            display_name=None,
            avatar_url=None,
            auth_provider=None,
            created_at=None,
        )
    return ProfileResponse(
        user_id=row["id"],
        email=row.get("email"),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        auth_provider=row.get("auth_provider"),
        created_at=row.get("created_at"),
    )


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(
    payload: ProfileUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ProfileResponse:
    name = payload.display_name.strip()
    if not name or len(name) > 60:
        # Fall back to current value silently if invalid
        row = get_profile_row(user.user_id)
        return ProfileResponse(
            user_id=user.user_id,
            email=row.get("email") if row else user.email,
            display_name=row.get("display_name") if row else None,
            avatar_url=row.get("avatar_url") if row else None,
            auth_provider=row.get("auth_provider") if row else None,
            created_at=row.get("created_at") if row else None,
        )

    updated = update_profile_display_name(user.user_id, name)
    return ProfileResponse(
        user_id=user.user_id,
        email=updated.get("email") if updated else user.email,
        display_name=updated.get("display_name") if updated else name,
        avatar_url=updated.get("avatar_url") if updated else None,
        auth_provider=updated.get("auth_provider") if updated else None,
        created_at=updated.get("created_at") if updated else None,
    )