from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_plan, require_verified
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models.user import User, SubscriptionPlan
from app.services.analytics_service import record_usage_event

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/free")
async def free_feature(
    current_user: User = Depends(require_verified()),
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limiter(max_requests=100, window_seconds=60)),
):
    """Available to all verified users (free plan+)."""
    await record_usage_event(db, current_user.id, "feature.free")
    await db.commit()
    return {"feature": "free_dashboard", "user": current_user.email}


@router.get("/pro")
async def pro_feature(
    current_user: User = Depends(require_plan(SubscriptionPlan.pro)),
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limiter(max_requests=300, window_seconds=60)),
):
    """Available to Pro plan and above only."""
    await record_usage_event(db, current_user.id, "feature.pro")
    await db.commit()
    return {"feature": "advanced_analytics", "user": current_user.email, "plan": current_user.plan}


@router.get("/enterprise")
async def enterprise_feature(
    current_user: User = Depends(require_plan(SubscriptionPlan.enterprise)),
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limiter(max_requests=1000, window_seconds=60)),
):
    """Enterprise plan only."""
    await record_usage_event(db, current_user.id, "feature.enterprise")
    await db.commit()
    return {"feature": "white_label", "user": current_user.email, "plan": current_user.plan}
