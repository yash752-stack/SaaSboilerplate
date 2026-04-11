from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    billing,
    files,
    health,
    notifications,
    orgs,
    protected,
    security,
    users,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(protected.router)
api_router.include_router(billing.router)
api_router.include_router(orgs.router)
api_router.include_router(files.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
api_router.include_router(webhooks.router)
api_router.include_router(security.router)
