import hashlib
import hmac
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.tasks.webhook_tasks import deliver_webhook


async def create_webhook_endpoint(
    db: AsyncSession,
    user_id: str,
    url: str,
    events: list[str],
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(
        user_id=user_id,
        url=url,
        secret=secrets.token_urlsafe(24),
        events=events,
    )
    db.add(endpoint)
    await db.flush()
    return endpoint


async def list_webhook_endpoints(db: AsyncSession, user_id: str) -> list[WebhookEndpoint]:
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user_id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return list(result.scalars().all())


async def dispatch_event(
    db: AsyncSession,
    endpoint: WebhookEndpoint,
    event_name: str,
    payload: dict,
) -> WebhookDelivery:
    signature = hmac.new(
        endpoint.secret.encode("utf-8"),
        str(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    delivery = WebhookDelivery(
        webhook_id=endpoint.id,
        event_name=event_name,
        status="queued",
    )
    db.add(delivery)
    await db.flush()

    try:
        deliver_webhook.delay(
            delivery.id,
            endpoint.url,
            event_name,
            payload,
            signature,
        )
    except Exception:
        delivery.status = "queued_local_only"
        db.add(delivery)
    endpoint.last_delivery_at = datetime.utcnow()
    db.add(endpoint)
    await db.flush()
    return delivery
