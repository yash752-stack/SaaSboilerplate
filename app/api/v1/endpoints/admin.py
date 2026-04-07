from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.db.base import get_db
from app.core.permissions import require_role
from app.models.user import User, UserRole, SubscriptionPlan
from app.schemas.user import UserResponse
from app.schemas.auth import MessageResponse
from app.core.rate_limit import rate_limiter

router = APIRouter(prefix="/admin", tags=["admin"])

# All admin routes require admin role
AdminDep = Depends(require_role(UserRole.admin))


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = AdminDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    plan: SubscriptionPlan | None = None,
    is_active: bool | None = None,
):
    """Admin: list all users with filters + pagination."""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if plan:
        query = query.where(User.plan == plan)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats")
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    _: User = AdminDep,
):
    """Admin: platform-wide stats."""
    total = await db.scalar(select(func.count(User.id)))
    active = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    verified = await db.scalar(select(func.count(User.id)).where(User.is_verified == True))

    plan_counts = {}
    for plan in SubscriptionPlan:
        count = await db.scalar(
            select(func.count(User.id)).where(User.plan == plan)
        )
        plan_counts[plan.value] = count

    return {
        "total_users": total,
        "active_users": active,
        "verified_users": verified,
        "plans": plan_counts,
    }


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    _: User = AdminDep,
):
    """Admin: change a user's role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = role
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/plan", response_model=UserResponse)
async def change_user_plan(
    user_id: uuid.UUID,
    plan: SubscriptionPlan,
    db: AsyncSession = Depends(get_db),
    _: User = AdminDep,
):
    """Admin: manually change a user's subscription plan."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.plan = plan
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=MessageResponse)
async def admin_deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = AdminDep,
):
    """Admin: deactivate any user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False
    db.add(user)
    await db.flush()
    return MessageResponse(message=f"User {user_id} deactivated")
