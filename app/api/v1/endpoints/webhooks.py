from pydantic import AnyHttpUrl, BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.plan_rate_limit import require_plan_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.models.webhook import WebhookEndpoint
from app.services.analytics_service import record_usage_event
from app.services.audit_service import log_audit
from app.services.webhook_service import create_webhook_endpoint, dispatch_event, list_webhook_endpoints

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    url: AnyHttpUrl
    events: list[str] = ["invoice.created", "notification.created"]


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    endpoints = await list_webhook_endpoints(db, current_user.id)
    return [
        {"id": endpoint.id, "url": endpoint.url, "events": endpoint.events, "is_active": endpoint.is_active}
        for endpoint in endpoints
    ]


@router.post("")
async def create_webhook(
    payload: CreateWebhookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _plan_limit=Depends(require_plan_rate_limit()),
):
    endpoint = await create_webhook_endpoint(db, current_user.id, str(payload.url), payload.events)
    await log_audit(db, current_user.id, "webhook.create", "webhook", endpoint.id, {"url": endpoint.url})
    await db.commit()
    return {"id": endpoint.id, "secret": endpoint.secret}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _plan_limit=Depends(require_plan_rate_limit()),
):
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.user_id == current_user.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    delivery = await dispatch_event(
        db,
        endpoint,
        "webhook.test",
        {"message": "Test webhook", "user_id": current_user.id},
    )
    await record_usage_event(db, current_user.id, "webhook.test")
    await db.commit()
    return {"delivery_id": delivery.id, "status": delivery.status}
