from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import list_notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items = await list_notifications(db, current_user.id)
    return [
        {
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "type": item.type,
            "is_read": item.is_read,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.add(notification)
    await db.commit()
    return {"message": "Marked as read"}
