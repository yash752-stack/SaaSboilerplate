from app.utils.tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
    verify_email_token,
    verify_password_reset_token,
)


class VerificationService:
    @staticmethod
    def create_email_verification_token(user_id: str) -> str:
        return generate_email_verification_token(user_id)

    @staticmethod
    def consume_email_verification_token(token: str) -> str | None:
        return verify_email_token(token)

    @staticmethod
    def create_password_reset_token(user_id: str) -> str:
        return generate_password_reset_token(user_id)

    @staticmethod
    def consume_password_reset_token(token: str) -> str | None:
        return verify_password_reset_token(token)
