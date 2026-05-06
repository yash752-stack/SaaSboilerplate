import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.celery_app import celery_app

logger = logging.getLogger("saas.tasks.user")


@celery_app.task(
    name="app.tasks.user_tasks.cleanup_expired_tokens",
    queue="default",
)
def cleanup_expired_tokens():
    """
    Periodic task (runs daily via Celery Beat).
    Redis TTLs handle expiry automatically — this logs stats.
    Extend here to purge soft-deleted users, stale sessions, etc.
    """
    import redis as _redis
    from app.core.config import settings

    r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
    ev_keys = len(r.keys("ev:*"))
    pr_keys = len(r.keys("pr:*"))
    bl_keys = len(r.keys("bl:*"))

    logger.info(
        f"[cleanup] email_verify={ev_keys} | password_reset={pr_keys} | blacklisted_jwt={bl_keys}"
    )
    return {"email_verify": ev_keys, "password_reset": pr_keys, "blacklisted": bl_keys}


@celery_app.task(
    name="app.tasks.user_tasks.send_plan_expiry_reminders",
    queue="default",
)
def send_plan_expiry_reminders():
    return asyncio.run(_send_plan_expiry_reminders())


async def _send_plan_expiry_reminders():
    from app.db.session import AsyncSessionLocal
    from app.models.subscription import Subscription
    from app.services.notification_service import create_notification

    reminder_window_end = datetime.utcnow() + timedelta(days=7)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.cancel_at_period_end == True,
                Subscription.status == "active",
                Subscription.current_period_end.is_not(None),
                Subscription.current_period_end <= reminder_window_end,
            )
        )
        subscriptions = result.scalars().all()

        reminders_sent = 0
        for subscription in subscriptions:
            await create_notification(
                db,
                subscription.user_id,
                "Subscription ending soon",
                "Your plan is scheduled to end within the next 7 days. Update billing to avoid service interruption.",
                "billing",
                {
                    "subscription_id": subscription.id,
                    "current_period_end": subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None,
                },
            )
            reminders_sent += 1

        await db.commit()

    logger.info("[plan_expiry] reminders_sent=%s", reminders_sent)
    return {"status": "completed", "reminders_sent": reminders_sent}
