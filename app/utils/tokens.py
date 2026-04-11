import redis
from datetime import timedelta
from datetime import datetime, timezone
import secrets
import logging
from app.core.config import settings

logger = logging.getLogger("saas.tokens")

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
_memory_store: dict[str, tuple[str, datetime]] = {}

EMAIL_VERIFY_PREFIX = "ev:"
PASSWORD_RESET_PREFIX = "pr:"
TOKEN_BLACKLIST_PREFIX = "bl:"

EMAIL_VERIFY_TTL = int(timedelta(hours=24).total_seconds())
PASSWORD_RESET_TTL = int(timedelta(hours=1).total_seconds())
BLACKLIST_TTL = int(timedelta(days=8).total_seconds())


def generate_email_verification_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    key = f"{EMAIL_VERIFY_PREFIX}{token}"
    _set_with_fallback(key, EMAIL_VERIFY_TTL, user_id)
    logger.info(f"Email verification token created for user {user_id}")
    return token


def verify_email_token(token: str) -> str | None:
    """Returns user_id if token is valid, else None."""
    key = f"{EMAIL_VERIFY_PREFIX}{token}"
    return _get_once(key)


def generate_password_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    key = f"{PASSWORD_RESET_PREFIX}{token}"
    _set_with_fallback(key, PASSWORD_RESET_TTL, user_id)
    logger.info(f"Password reset token created for user {user_id}")
    return token


def verify_password_reset_token(token: str) -> str | None:
    """Returns user_id if token is valid, else None."""
    key = f"{PASSWORD_RESET_PREFIX}{token}"
    return _get_once(key)


def blacklist_token(jti: str) -> None:
    """Add a JWT jti to the blacklist (for logout)."""
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    _set_with_fallback(key, BLACKLIST_TTL, "1")


def is_token_blacklisted(jti: str) -> bool:
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    try:
        return _redis.exists(key) == 1
    except Exception:
        item = _memory_store.get(key)
        if not item:
            return False
        _, expires_at = item
        if expires_at <= datetime.now(timezone.utc):
            _memory_store.pop(key, None)
            return False
        return True


def _set_with_fallback(key: str, ttl: int, value: str) -> None:
    try:
        _redis.setex(key, ttl, value)
    except Exception:
        _memory_store[key] = (value, datetime.now(timezone.utc) + timedelta(seconds=ttl))


def _get_once(key: str) -> str | None:
    try:
        value = _redis.get(key)
        if value:
            _redis.delete(key)
        return value
    except Exception:
        item = _memory_store.pop(key, None)
        if not item:
            return None
        value, expires_at = item
        if expires_at <= datetime.now(timezone.utc):
            return None
        return value
