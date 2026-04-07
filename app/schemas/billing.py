from pydantic import BaseModel
from typing import Optional
from app.models.user import SubscriptionPlan


class CreateCheckoutRequest(BaseModel):
    plan: SubscriptionPlan
    success_url: str = "http://localhost:3000/billing/success"
    cancel_url: str = "http://localhost:3000/billing/cancel"


class CreatePortalRequest(BaseModel):
    return_url: str = "http://localhost:3000/billing"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionStatus(BaseModel):
    plan: SubscriptionPlan
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    is_active: bool


class PlanInfo(BaseModel):
    name: str
    price_monthly_usd: float
    features: list[str]
    stripe_price_id: str
