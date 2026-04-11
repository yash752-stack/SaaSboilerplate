from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.tasks.email_tasks import send_password_reset_email, send_verification_email, send_welcome_email
from app.utils.tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
    verify_email_token,
    verify_password_reset_token,
)


def _safe_delay(task, *args):
    try:
        task.delay(*args)
    except Exception:
        return None
    return True


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> User:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(email=data.email, hashed_password=hash_password(data.password), full_name=data.full_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        token = generate_email_verification_token(user.id)
        _safe_delay(send_verification_email, user.email, user.full_name or "", token, settings.BACKEND_BASE_URL)
        return user

    @staticmethod
    async def login(db: AsyncSession, data: UserLogin) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        if user.two_factor_enabled:
            import pyotp

            if not data.totp_code:
                raise HTTPException(status_code=401, detail="Two-factor code required")
            totp = pyotp.TOTP(user.two_factor_secret or "")
            if not totp.verify(data.totp_code, valid_window=1):
                raise HTTPException(status_code=401, detail="Invalid two-factor code")
        access_token = create_access_token(user.id, extra={"role": user.role})
        refresh_token = create_refresh_token(user.id)
        user.refresh_token = refresh_token
        await db.commit()
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    @staticmethod
    async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Wrong token type")
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user or user.refresh_token != refresh_token:
            raise HTTPException(status_code=401, detail="Token reuse detected")
        access_token = create_access_token(user.id, extra={"role": user.role})
        new_refresh = create_refresh_token(user.id)
        user.refresh_token = new_refresh
        await db.commit()
        return TokenResponse(access_token=access_token, refresh_token=new_refresh)

    @staticmethod
    async def logout(db: AsyncSession, user_id: str) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.refresh_token = None
            await db.commit()

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> User:
        user_id = verify_email_token(token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_verified = True
        db.add(user)
        await db.commit()
        await db.refresh(user)
        _safe_delay(send_welcome_email, user.email, user.full_name or "")
        return user

    @staticmethod
    async def forgot_password(db: AsyncSession, email: str) -> None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return

        token = generate_password_reset_token(user.id)
        _safe_delay(send_password_reset_email, user.email, user.full_name or "", token, settings.BACKEND_BASE_URL)

    @staticmethod
    async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
        user_id = verify_password_reset_token(token)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = hash_password(new_password)
        user.refresh_token = None
        db.add(user)
        await db.commit()

    @staticmethod
    async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        user.hashed_password = hash_password(new_password)
        user.refresh_token = None
        db.add(user)
        await db.commit()
