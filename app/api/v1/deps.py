from fastapi import Depends, HTTPException

from app.core.deps import (
    get_current_active_user,
    get_current_admin,
    get_current_user,
)
from app.models.user import User


def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        normalized_roles = {getattr(role, "value", role) for role in roles}
        current_role = getattr(current_user.role, "value", current_user.role)
        if current_role not in normalized_roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {' or '.join(sorted(normalized_roles))}")
        return current_user

    return _check


require_admin = require_role("admin")

__all__ = ["get_current_user", "get_current_active_user", "get_current_admin", "require_admin", "require_role"]
