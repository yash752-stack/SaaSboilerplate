from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_event import UsageEvent


async def record_usage_event(
    db: AsyncSession,
    user_id: str,
    event_name: str,
    quantity: int = 1,
    metadata: dict | None = None,
) -> UsageEvent:
    event = UsageEvent(
        user_id=user_id,
        event_name=event_name,
        quantity=quantity,
        metadata_json=metadata or {},
    )
    db.add(event)
    await db.flush()
    return event


async def get_usage_summary(db: AsyncSession, user_id: str, days: int = 30) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(UsageEvent.event_name, func.sum(UsageEvent.quantity))
        .where(UsageEvent.user_id == user_id, UsageEvent.created_at >= since)
        .group_by(UsageEvent.event_name)
        .order_by(UsageEvent.event_name.asc())
    )
    return [
        {"event_name": event_name, "total": total or 0}
        for event_name, total in result.all()
    ]


async def get_daily_usage(db: AsyncSession, user_id: str, days: int = 14) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(UsageEvent.created_at).label("day"),
            func.sum(UsageEvent.quantity).label("total"),
        )
        .where(UsageEvent.user_id == user_id, UsageEvent.created_at >= since)
        .group_by(func.date(UsageEvent.created_at))
        .order_by(func.date(UsageEvent.created_at).asc())
    )
    return [{"day": str(day), "total": total or 0} for day, total in result.all()]
