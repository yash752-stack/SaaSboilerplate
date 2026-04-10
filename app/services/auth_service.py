from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from fastapi import HTTPException, status
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
        return user
    @staticmethod
    async def login(db: AsyncSession, data: UserLogin) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
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
