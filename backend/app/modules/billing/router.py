from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["billing"])


@router.post("/whop")
def whop_webhook() -> dict:
    # Implemented in next step: HMAC verify, idempotency, entitlement update.
    return {"received": True, "implemented": False}