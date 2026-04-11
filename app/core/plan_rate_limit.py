from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.deps import get_current_active_user
from app.core.rate_limit import get_redis
from app.models.user import SubscriptionPlan, User

PLAN_LIMITS = {
    SubscriptionPlan.free: settings.API_RATE_LIMIT_FREE,
    SubscriptionPlan.pro: settings.API_RATE_LIMIT_PRO,
    SubscriptionPlan.enterprise: settings.API_RATE_LIMIT_ENTERPRISE,
}


def require_plan_rate_limit():
    async def _check(
        request: Request,
        current_user: User = Depends(get_current_active_user),
    ):
        try:
            redis = await get_redis()
            max_requests = PLAN_LIMITS.get(current_user.plan, settings.API_RATE_LIMIT_FREE)
            key = f"plan-rl:{current_user.id}:{request.url.path}"
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, 60)
            if current > max_requests:
                ttl = await redis.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Plan rate limit exceeded. Retry after {ttl}s",
                    headers={"Retry-After": str(ttl)},
                )
        except HTTPException:
            raise
        except Exception:
            pass

    return _check
