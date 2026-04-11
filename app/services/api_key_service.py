import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def create_api_key(
    db: AsyncSession,
    user_id: str,
    name: str,
    scopes: list[str],
) -> tuple[ApiKey, str]:
    raw_key = f"sk_live_{secrets.token_urlsafe(24)}"
    key = ApiKey(
        user_id=user_id,
        name=name,
        key_prefix=raw_key[:12],
        key_hash=_hash_key(raw_key),
        scopes=",".join(scopes or ["read"]),
    )
    db.add(key)
    await db.flush()
    return key, raw_key


async def list_api_keys(db: AsyncSession, user_id: str) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, user_id: str, key_id: str) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.revoked_at = datetime.utcnow()
    db.add(key)
    await db.flush()
    return True
