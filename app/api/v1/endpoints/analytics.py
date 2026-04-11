from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import get_daily_usage, get_usage_summary, record_usage_event
from app.services.invoice_service import generate_invoice

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_usage_summary(db, current_user.id)


@router.get("/daily")
async def daily(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_daily_usage(db, current_user.id)


@router.post("/track")
async def track(
    event_name: str,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await record_usage_event(db, current_user.id, event_name, quantity=quantity)
    await db.commit()
    return {"message": "Tracked"}


@router.post("/invoices/generate")
async def create_invoice(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    invoice = await generate_invoice(db, current_user.id)
    await db.commit()
    return {
        "id": invoice.id,
        "amount_usd": invoice.amount_usd,
        "status": invoice.status,
        "line_items": invoice.line_items,
    }
