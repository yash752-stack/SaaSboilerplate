import logging
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
    """
    Placeholder: query users whose subscriptions expire soon
    and enqueue reminder emails. Wire up with Stripe subscription data.
    """
    logger.info("[plan_expiry] reminder task triggered — implement with Stripe data")
    return {"status": "noop"}
