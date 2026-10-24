from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.modules.entitlements.deps import require_entitlement
from app.modules.entitlements.schemas import (
    EntitlementGrantedResponse,
    EntitlementStatusResponse,
)
from app.modules.entitlements.service import get_entitlement, is_entitled

router = APIRouter(prefix="/entitlement", tags=["entitlement"])


@router.get("/status", response_model=EntitlementStatusResponse)
def status(user: CurrentUser = Depends(get_current_user)) -> EntitlementStatusResponse:
    return EntitlementStatusResponse(
        user_id=user.user_id,
        is_active=is_entitled(user.user_id),
        entitlement=get_entitlement(user.user_id),
    )


@router.get("/require", response_model=EntitlementGrantedResponse)
def require(user: CurrentUser = Depends(require_entitlement)) -> EntitlementGrantedResponse:
    return EntitlementGrantedResponse(user_id=user.user_id, granted=True)