import redis
from datetime import timedelta
import secrets
import logging
from app.core.config import settings

logger = logging.getLogger("saas.tokens")

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

EMAIL_VERIFY_PREFIX = "ev:"
PASSWORD_RESET_PREFIX = "pr:"
TOKEN_BLACKLIST_PREFIX = "bl:"

EMAIL_VERIFY_TTL = int(timedelta(hours=24).total_seconds())
PASSWORD_RESET_TTL = int(timedelta(hours=1).total_seconds())
BLACKLIST_TTL = int(timedelta(days=8).total_seconds())


def generate_email_verification_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    key = f"{EMAIL_VERIFY_PREFIX}{token}"
    _redis.setex(key, EMAIL_VERIFY_TTL, user_id)
    logger.info(f"Email verification token created for user {user_id}")
    return token


def verify_email_token(token: str) -> str | None:
    """Returns user_id if token is valid, else None."""
    key = f"{EMAIL_VERIFY_PREFIX}{token}"
    user_id = _redis.get(key)
    if user_id:
        _redis.delete(key)  # one-time use
    return user_id


def generate_password_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    key = f"{PASSWORD_RESET_PREFIX}{token}"
    _redis.setex(key, PASSWORD_RESET_TTL, user_id)
    logger.info(f"Password reset token created for user {user_id}")
    return token


def verify_password_reset_token(token: str) -> str | None:
    """Returns user_id if token is valid, else None."""
    key = f"{PASSWORD_RESET_PREFIX}{token}"
    user_id = _redis.get(key)
    if user_id:
        _redis.delete(key)  # one-time use
    return user_id


def blacklist_token(jti: str) -> None:
    """Add a JWT jti to the blacklist (for logout)."""
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    _redis.setex(key, BLACKLIST_TTL, "1")


def is_token_blacklisted(jti: str) -> bool:
    key = f"{TOKEN_BLACKLIST_PREFIX}{jti}"
    return _redis.exists(key) == 1
