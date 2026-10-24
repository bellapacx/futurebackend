from fastapi import Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import SubscriptionRequiredError
from app.modules.entitlements.service import is_entitled


def require_entitlement(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Reusable dependency. Any indicator/marketdata endpoint that must be
    gated by active subscription declares `Depends(require_entitlement)`.
    """
    if not is_entitled(user.user_id):
        raise SubscriptionRequiredError()
    return user