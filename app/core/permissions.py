from fastapi import HTTPException, status, Depends
from app.models.user import User, UserRole, SubscriptionPlan
from app.core.deps import get_current_active_user

PLAN_HIERARCHY = {
    SubscriptionPlan.free: 0,
    SubscriptionPlan.pro: 1,
    SubscriptionPlan.enterprise: 2,
}


def require_plan(minimum_plan: SubscriptionPlan):
    """
    Dependency: ensures user is on at least `minimum_plan`.
    Usage: Depends(require_plan(SubscriptionPlan.pro))
    """
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        user_level = PLAN_HIERARCHY.get(current_user.plan, 0)
        required_level = PLAN_HIERARCHY.get(minimum_plan, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires the '{minimum_plan.value}' plan or higher. "
                       f"Your current plan is '{current_user.plan.value}'.",
            )
        return current_user

    return _check


def require_role(*roles: UserRole):
    """
    Dependency: ensures user has one of the given roles.
    Usage: Depends(require_role(UserRole.admin))
    """
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to roles: {[r.value for r in roles]}",
            )
        return current_user

    return _check


def require_verified():
    """Dependency: ensures user has verified their email."""
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. Please verify your email to access this resource.",
            )
        return current_user

    return _check
