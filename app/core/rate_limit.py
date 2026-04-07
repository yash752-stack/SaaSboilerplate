import redis.asyncio as aioredis
from fastapi import Request, HTTPException, status
from app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def rate_limiter(max_requests: int = 60, window_seconds: int = 60):
    """
    Dependency factory — use as:
        Depends(rate_limiter(max_requests=10, window_seconds=60))
    Identifies callers by IP. Authenticated routes can swap to user ID.
    """
    async def _check(request: Request):
        try:
            r = await get_redis()
            ip = request.client.host if request.client else "unknown"
            key = f"rl:{request.url.path}:{ip}"

            current = await r.incr(key)
            if current == 1:
                await r.expire(key, window_seconds)

            remaining = max_requests - current
            request.state.rate_limit_remaining = max(remaining, 0)

            if current > max_requests:
                ttl = await r.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Retry after {ttl}s",
                    headers={"Retry-After": str(ttl)},
                )
        except HTTPException:
            raise
        except Exception:
            # If Redis is down, fail open (don't block requests)
            pass

    return _check
