from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.base import get_db
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.deps import get_current_active_user
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    AccessTokenResponse,
    MessageResponse,
)
from app.schemas.user import UserResponse
from app.schemas.password import ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from app.services.user_service import create_user, get_user_by_email, get_user_by_id
from app.models.user import User
from app.utils.tokens import (
    generate_email_verification_token,
    verify_email_token,
    generate_password_reset_token,
    verify_password_reset_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user and send verification email."""
    user = await create_user(db, payload)

    # Enqueue verification email via Celery (non-blocking)
    try:
        from app.tasks.email_tasks import send_verification_email
        token = generate_email_verification_token(str(user.id))
        base_url = str(request.base_url).rstrip("/")
        send_verification_email.delay(
            email=user.email,
            full_name=user.full_name or "",
            token=token,
            base_url=base_url,
        )
    except Exception:
        pass  # Don't fail registration if Celery/Redis is down

    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and get JWT access + refresh tokens."""
    user = await get_user_by_email(db, payload.email)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token(
        subject=str(user.id),
        extra={"role": user.role.value, "plan": user.plan.value},
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Use refresh token to get a new access token."""
    token_data = decode_token(payload.refresh_token)

    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await get_user_by_id(db, uuid.UUID(token_data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    access_token = create_access_token(
        subject=str(user.id),
        extra={"role": user.role.value, "plan": user.plan.value},
    )
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout — client discards tokens. Day 5 adds Redis blacklist."""
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user."""
    return current_user


# ── Email Verification ───────────────────────────────────────────────────────

@router.post("/send-verification", response_model=MessageResponse)
async def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Resend email verification link."""
    if current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")

    try:
        from app.tasks.email_tasks import send_verification_email
        token = generate_email_verification_token(str(current_user.id))
        base_url = str(request.base_url).rstrip("/")
        send_verification_email.delay(
            email=current_user.email,
            full_name=current_user.full_name or "",
            token=token,
            base_url=base_url,
        )
    except Exception:
        pass

    return MessageResponse(message="Verification email sent. Check your inbox.")


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify email using the token from the verification link."""
    user_id = verify_email_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    db.add(user)
    await db.flush()

    # Send welcome email
    try:
        from app.tasks.email_tasks import send_welcome_email
        send_welcome_email.delay(email=user.email, full_name=user.full_name or "")
    except Exception:
        pass

    return MessageResponse(message="Email verified successfully! Welcome aboard.")


# ── Password Reset ───────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email."""
    user = await get_user_by_email(db, payload.email)

    # Always return success to prevent email enumeration
    if user and user.is_active:
        try:
            from app.tasks.email_tasks import send_password_reset_email
            token = generate_password_reset_token(str(user.id))
            base_url = str(request.base_url).rstrip("/")
            send_password_reset_email.delay(
                email=user.email,
                full_name=user.full_name or "",
                token=token,
                base_url=base_url,
            )
        except Exception:
            pass

    return MessageResponse(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token from email."""
    user_id = verify_password_reset_token(payload.token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    await db.flush()

    return MessageResponse(message="Password reset successfully. Please log in.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Change password while logged in."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    db.add(current_user)
    await db.flush()

    return MessageResponse(message="Password changed successfully.")
