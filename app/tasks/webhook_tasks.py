import httpx

from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.webhook_tasks.deliver_webhook", queue="webhooks")
def deliver_webhook(delivery_id: str, url: str, event_name: str, payload: dict, signature: str):
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event_name,
        "X-Webhook-Signature": signature,
        "X-Webhook-Delivery-ID": delivery_id,
    }
    try:
        httpx.post(url, json=payload, headers=headers, timeout=10.0)
    except Exception:
        return {"delivery_id": delivery_id, "status": "failed"}
    return {"delivery_id": delivery_id, "status": "delivered"}
