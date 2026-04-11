import base64
import io

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key
from app.services.audit_service import log_audit
from app.services.notification_service import create_notification

router = APIRouter(prefix="/security", tags=["security"])


class TwoFactorCodeRequest(BaseModel):
    code: str


class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = ["read"]


@router.post("/2fa/setup")
async def setup_two_factor(current_user: User = Depends(get_current_active_user)):
    import pyotp
    import qrcode

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="SaaS Boilerplate")
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    png_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return {"secret": secret, "otpauth_url": uri, "qr_png_base64": png_b64}


@router.post("/2fa/enable")
async def enable_two_factor(
    payload: TwoFactorCodeRequest,
    secret: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    import pyotp

    totp = pyotp.TOTP(secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.two_factor_secret = secret
    current_user.two_factor_enabled = True
    db.add(current_user)
    await log_audit(db, current_user.id, "2fa.enable", "user", current_user.id)
    await create_notification(db, current_user.id, "2FA enabled", "Two-factor authentication is now active.")
    await db.commit()
    return {"message": "Two-factor authentication enabled"}


@router.post("/2fa/disable")
async def disable_two_factor(
    payload: TwoFactorCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    import pyotp

    if not current_user.two_factor_enabled or not current_user.two_factor_secret:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.add(current_user)
    await log_audit(db, current_user.id, "2fa.disable", "user", current_user.id)
    await db.commit()
    return {"message": "Two-factor authentication disabled"}


@router.get("/api-keys")
async def api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    keys = await list_api_keys(db, current_user.id)
    return [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "scopes": key.scopes.split(",") if key.scopes else [],
            "created_at": key.created_at,
            "revoked_at": key.revoked_at,
        }
        for key in keys
    ]


@router.post("/api-keys")
async def new_api_key(
    payload: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    key, raw_key = await create_api_key(db, current_user.id, payload.name, payload.scopes)
    await log_audit(db, current_user.id, "api_key.create", "api_key", key.id, {"name": payload.name})
    await create_notification(db, current_user.id, "API key created", f"{payload.name} is ready to use.")
    await db.commit()
    return {"id": key.id, "api_key": raw_key}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    revoked = await revoke_api_key(db, current_user.id, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    await log_audit(db, current_user.id, "api_key.revoke", "api_key", key_id)
    await db.commit()
    return {"message": "API key revoked"}
