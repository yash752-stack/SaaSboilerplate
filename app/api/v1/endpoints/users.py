from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.core.deps import get_current_active_user, get_current_admin
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.auth import MessageResponse
from app.services.user_service import update_user, deactivate_user, get_user_by_id
from app.models.user import User
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update current user profile."""
    return await update_user(db, current_user, payload)


@router.delete("/me", response_model=MessageResponse)
async def deactivate_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Deactivate current user account."""
    await deactivate_user(db, current_user)
    return MessageResponse(message="Account deactivated successfully")


# ── Admin only ──────────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: get any user by ID."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
