import logging
from app.core.celery_app import celery_app
from app.utils.email import (
    send_email,
    render_verification_email,
    render_password_reset_email,
    render_welcome_email,
)

logger = logging.getLogger("saas.tasks.email")


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_verification_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_verification_email(self, email: str, full_name: str, token: str, base_url: str):
    """Send email verification link. Retries up to 3 times on failure."""
    try:
        verify_url = f"{base_url}/api/v1/auth/verify-email?token={token}"
        html = render_verification_email(full_name, verify_url)
        success = send_email(to=email, subject="Verify your email", html_body=html)
        if not success:
            raise Exception("send_email returned False")
        logger.info(f"Verification email sent → {email}")
    except Exception as exc:
        logger.error(f"send_verification_email failed for {email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.tasks.email_tasks.send_password_reset_email",
    max_retries=3,
    default_retry_delay=60,
    queue="email",
)
def send_password_reset_email(self, email: str, full_name: str, token: str, base_url: str):
    """Send password reset link."""
    try:
        reset_url = f"{base_url}/api/v1/auth/reset-password?token={token}"
        html = render_password_reset_email(full_name, reset_url)
        success = send_email(to=email, subject="Reset your password", html_body=html)
        if not success:
            raise Exception("send_email returned False")
        logger.info(f"Password reset email sent → {email}")
    except Exception as exc:
        logger.error(f"send_password_reset_email failed for {email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.email_tasks.send_welcome_email",
    queue="email",
)
def send_welcome_email(email: str, full_name: str):
    """Send welcome email after successful email verification."""
    html = render_welcome_email(full_name)
    send_email(to=email, subject="Welcome! Your account is ready 🎉", html_body=html)
    logger.info(f"Welcome email sent → {email}")
