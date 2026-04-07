from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.core.deps import get_current_active_user
from app.models.user import User, SubscriptionPlan
from app.schemas.billing import (
    CreateCheckoutRequest,
    CreatePortalRequest,
    CheckoutResponse,
    PortalResponse,
    SubscriptionStatus,
    PlanInfo,
)
from app.services.billing_service import (
    create_checkout_session,
    create_billing_portal,
    cancel_subscription,
    handle_webhook_event,
    PLAN_DETAILS,
)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    """List all available subscription plans and pricing."""
    return [
        PlanInfo(
            name=details["name"],
            price_monthly_usd=details["price_monthly_usd"],
            features=details["features"],
            stripe_price_id=details["stripe_price_id"],
        )
        for details in PLAN_DETAILS.values()
    ]


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's subscription status."""
    return SubscriptionStatus(
        plan=current_user.plan,
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        is_active=current_user.is_active,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a Stripe Checkout session to upgrade plan."""
    result = await create_checkout_session(
        db=db,
        user=current_user,
        plan=payload.plan,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return CheckoutResponse(**result)


@router.post("/portal", response_model=PortalResponse)
async def open_billing_portal(
    payload: CreatePortalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Open Stripe Customer Portal to manage subscription."""
    url = await create_billing_portal(db, current_user, payload.return_url)
    return PortalResponse(portal_url=url)


@router.post("/cancel")
async def cancel_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel subscription at period end."""
    await cancel_subscription(db, current_user)
    return {"message": "Subscription will cancel at the end of the billing period"}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook endpoint.
    Set this URL in your Stripe dashboard:
    https://yourdomain.com/api/v1/billing/webhook
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    return await handle_webhook_event(db, payload, sig_header)
