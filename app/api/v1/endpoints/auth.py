from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserOut
from app.services.auth_service import AuthService
from app.api.v1.deps import get_current_user
from app.models.user import User
router = APIRouter(prefix="/auth", tags=["auth"])
@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    return await AuthService.register(db, data)
@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await AuthService.login(db, data)
@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService.refresh(db, data.refresh_token)
@router.post("/logout", status_code=204)
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuthService.logout(db, current_user.id)
@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
