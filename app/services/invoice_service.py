from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.usage_event import UsageEvent

UNIT_PRICES = {
    "feature.free": 0.0,
    "feature.pro": 0.02,
    "feature.enterprise": 0.05,
    "files.presign": 0.01,
    "webhook.test": 0.03,
}


async def generate_invoice(db: AsyncSession, user_id: str, days: int = 30) -> Invoice:
    period_end = datetime.utcnow()
    period_start = period_end - timedelta(days=days)

    result = await db.execute(
        select(UsageEvent).where(
            UsageEvent.user_id == user_id,
            UsageEvent.created_at >= period_start,
            UsageEvent.created_at <= period_end,
        )
    )
    events = list(result.scalars().all())

    line_items: list[dict] = []
    total = 0.0
    for event in events:
        price = UNIT_PRICES.get(event.event_name, 0.0)
        subtotal = round(price * event.quantity, 2)
        total += subtotal
        line_items.append(
            {
                "event_name": event.event_name,
                "quantity": event.quantity,
                "unit_price": price,
                "subtotal": subtotal,
            }
        )

    invoice = Invoice(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        amount_usd=round(total, 2),
        status="draft",
        line_items=line_items,
    )
    db.add(invoice)
    await db.flush()
    return invoice
