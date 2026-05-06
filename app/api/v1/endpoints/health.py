from sqlalchemy import text
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.core.config import settings
from app.core.rate_limit import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/live")
async def liveness_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/db")
async def db_health_check(response: Response, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": str(e)}


@router.get("/health/ready")
async def readiness_check(response: Response, db: AsyncSession = Depends(get_db)):
    checks = {
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }

    overall_ok = True

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        overall_ok = False

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = {"status": "ok"}
    except Exception as exc:
        checks["redis"] = {"status": "error", "detail": str(exc)}
        overall_ok = False

    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if overall_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": checks,
    }
