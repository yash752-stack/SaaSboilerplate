from sqlalchemy import select, func
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.subscription import Subscription
from app.models.user import SubscriptionPlan, User, UserRole
from app.schemas.auth import UserOut
from app.services.audit_service import log_audit


router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    q = select(User)
    cq = select(func.count()).select_from(User)
    if search:
        q = q.where(User.email.ilike(f"%{search}%"))
        cq = cq.where(User.email.ilike(f"%{search}%"))
    total = (await db.execute(cq)).scalar()
    users = (
        await db.execute(q.offset(offset).limit(per_page).order_by(User.created_at.desc()))
    ).scalars().all()
    return {"total": total, "page": page, "per_page": per_page, "users": users}


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be user or admin")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = UserRole(body.role)
    await log_audit(
        db,
        admin_user.id,
        "admin.user.role.update",
        "user",
        user.id,
        {"role": user.role.value},
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    user.refresh_token = None
    await log_audit(
        db,
        admin_user.id,
        "admin.user.deactivate",
        "user",
        user.id,
        {"is_active": False},
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/stats")
async def platform_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar()
    active = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active == True))
    ).scalar()
    pro = (
        await db.execute(
            select(func.count()).select_from(Subscription).where(Subscription.plan == SubscriptionPlan.pro)
        )
    ).scalar()
    ent = (
        await db.execute(
            select(func.count()).select_from(Subscription).where(
                Subscription.plan == SubscriptionPlan.enterprise
            )
        )
    ).scalar()
    return {
        "total_users": total,
        "active_users": active,
        "subscriptions": {
            "free": total - pro - ent,
            "pro": pro,
            "enterprise": ent,
        },
    }


@router.get("/audit-logs")
async def audit_logs(
    limit: int = Query(50, ge=1, le=200),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "metadata": log.metadata_json,
            "created_at": log.created_at,
        }
        for log in logs
    ]
