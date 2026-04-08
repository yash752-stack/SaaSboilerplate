from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "saas_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.email_tasks", "app.tasks.user_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.user_tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "cleanup-expired-tokens-daily": {
            "task": "app.tasks.user_tasks.cleanup_expired_tokens",
            "schedule": 86400.0,  # every 24 hours
        },
    },
)
