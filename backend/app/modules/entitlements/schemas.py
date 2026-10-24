from pydantic import BaseModel


class EntitlementStatusResponse(BaseModel):
    user_id: str
    is_active: bool
    entitlement: dict | None


class EntitlementGrantedResponse(BaseModel):
    user_id: str
    granted: bool