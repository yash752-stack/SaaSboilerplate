import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger("saas.email")


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to

        part = MIMEText(html_body, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())

        logger.info(f"Email sent to {to} | subject='{subject}'")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def render_verification_email(full_name: str, verify_url: str) -> str:
    name = full_name or "there"
    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:32px">
      <h2 style="color:#1a1a1a">Verify your email</h2>
      <p>Hi {name},</p>
      <p>Click the button below to verify your email address:</p>
      <a href="{verify_url}" style="display:inline-block;background:#4f46e5;color:#fff;
         padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0">
        Verify Email
      </a>
      <p style="color:#666;font-size:13px">This link expires in 24 hours.<br>
      If you didn't create an account, ignore this email.</p>
    </body></html>
    """


def render_password_reset_email(full_name: str, reset_url: str) -> str:
    name = full_name or "there"
    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:32px">
      <h2 style="color:#1a1a1a">Reset your password</h2>
      <p>Hi {name},</p>
      <p>We received a request to reset your password. Click the button below:</p>
      <a href="{reset_url}" style="display:inline-block;background:#dc2626;color:#fff;
         padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0">
        Reset Password
      </a>
      <p style="color:#666;font-size:13px">This link expires in 1 hour.<br>
      If you didn't request this, ignore this email.</p>
    </body></html>
    """


def render_welcome_email(full_name: str) -> str:
    name = full_name or "there"
    return f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:auto;padding:32px">
      <h2 style="color:#1a1a1a">Welcome aboard! 🎉</h2>
      <p>Hi {name},</p>
      <p>Your account is verified and ready to go.</p>
      <p>Head back to the app and start building.</p>
      <p style="color:#666;font-size:13px">Need help? Reply to this email anytime.</p>
    </body></html>
    """
