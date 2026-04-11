from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.websocket.manager import manager


async def create_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    body: str,
    type_: str = "info",
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        body=body,
        type=type_,
        payload=payload or {},
    )
    db.add(notification)
    await db.flush()
    await manager.send_to_user(
        user_id,
        {
            "type": "notification",
            "title": title,
            "body": body,
            "payload": payload or {},
        },
    )
    return notification


async def list_notifications(db: AsyncSession, user_id: str) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())
