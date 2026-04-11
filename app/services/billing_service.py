import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.models.subscription import Subscription
from app.models.user import User, SubscriptionPlan

stripe.api_key = settings.STRIPE_SECRET_KEY

# Map plans → Stripe Price IDs (set these in your .env or Stripe dashboard)
PLAN_PRICE_IDS: dict[SubscriptionPlan, str] = {
    SubscriptionPlan.pro: settings.STRIPE_PRO_PRICE_ID,
    SubscriptionPlan.enterprise: settings.STRIPE_ENTERPRISE_PRICE_ID,
}

PLAN_DETAILS = {
    SubscriptionPlan.free: {
        "name": "Free",
        "price_monthly_usd": 0.0,
        "stripe_price_id": "",
        "features": ["5 API calls/day", "Basic dashboard", "Community support"],
    },
    SubscriptionPlan.pro: {
        "name": "Pro",
        "price_monthly_usd": 19.0,
        "stripe_price_id": PLAN_PRICE_IDS[SubscriptionPlan.pro],
        "features": ["Unlimited API calls", "Advanced analytics", "Priority support", "Webhooks"],
    },
    SubscriptionPlan.enterprise: {
        "name": "Enterprise",
        "price_monthly_usd": 99.0,
        "stripe_price_id": PLAN_PRICE_IDS[SubscriptionPlan.enterprise],
        "features": ["Everything in Pro", "White labelling", "SLA 99.9%", "Dedicated account manager"],
    },
}


async def get_or_create_stripe_customer(db: AsyncSession, user: User) -> str:
    """Return existing Stripe customer ID or create a new one."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name or user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    db.add(user)
    await db.flush()
    return customer.id


async def create_checkout_session(
    db: AsyncSession,
    user: User,
    plan: SubscriptionPlan,
    success_url: str,
    cancel_url: str,
) -> dict:
    if plan == SubscriptionPlan.free:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot checkout for free plan",
        )

    price_id = PLAN_PRICE_IDS.get(plan)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No Stripe price configured for plan: {plan.value}",
        )

    customer_id = await get_or_create_stripe_customer(db, user)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan": plan.value},
        subscription_data={
            "metadata": {"user_id": str(user.id), "plan": plan.value}
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


async def create_billing_portal(
    db: AsyncSession,
    user: User,
    return_url: str,
) -> str:
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Subscribe to a plan first.",
        )

    portal = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return portal.url


async def cancel_subscription(db: AsyncSession, user: User) -> User:
    if not user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription found",
        )

    stripe.Subscription.modify(
        user.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    return user


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str):
    """Process Stripe webhook events and update DB accordingly."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature",
        )

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)

    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

    return {"status": "handled", "event": event_type}


async def _handle_checkout_completed(db: AsyncSession, session: dict):
    user_id = session.get("metadata", {}).get("user_id")
    plan_str = session.get("metadata", {}).get("plan")
    subscription_id = session.get("subscription")

    if not user_id or not plan_str:
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan = SubscriptionPlan(plan_str)
    user.stripe_subscription_id = subscription_id
    await _sync_subscription_row(
        db,
        user=user,
        plan=user.plan,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=user.stripe_customer_id,
        status="active",
    )
    db.add(user)
    await db.flush()


async def _handle_subscription_updated(db: AsyncSession, subscription: dict):
    user_id = subscription.get("metadata", {}).get("user_id")
    if not user_id:
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    stripe_status = subscription.get("status")
    if stripe_status == "active":
        plan_str = subscription.get("metadata", {}).get("plan")
        if plan_str:
            user.plan = SubscriptionPlan(plan_str)
    elif stripe_status in ("canceled", "unpaid", "past_due"):
        user.plan = SubscriptionPlan.free
        user.stripe_subscription_id = None

    await _sync_subscription_row(
        db,
        user=user,
        plan=user.plan,
        stripe_subscription_id=user.stripe_subscription_id,
        stripe_customer_id=user.stripe_customer_id,
        status=stripe_status or "active",
    )
    db.add(user)
    await db.flush()


async def _handle_subscription_deleted(db: AsyncSession, subscription: dict):
    user_id = subscription.get("metadata", {}).get("user_id")
    if not user_id:
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan = SubscriptionPlan.free
    user.stripe_subscription_id = None
    await _sync_subscription_row(
        db,
        user=user,
        plan=SubscriptionPlan.free,
        stripe_subscription_id=None,
        stripe_customer_id=user.stripe_customer_id,
        status="canceled",
    )
    db.add(user)
    await db.flush()


async def _handle_payment_failed(db: AsyncSession, invoice: dict):
    import logging
    logger = logging.getLogger("saas.billing")
    customer_id = invoice.get("customer")
    logger.warning(f"Payment failed for Stripe customer: {customer_id}")


async def _sync_subscription_row(
    db: AsyncSession,
    user: User,
    plan: SubscriptionPlan,
    stripe_subscription_id: str | None,
    stripe_customer_id: str | None,
    status: str,
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    subscription = result.scalar_one_or_none()
    if not subscription:
        subscription = Subscription(user_id=user.id)
    subscription.plan = plan
    subscription.status = status
    subscription.stripe_customer_id = stripe_customer_id
    subscription.stripe_subscription_id = stripe_subscription_id
    db.add(subscription)
