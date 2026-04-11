from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SaaS Boilerplate"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./saas.db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = "price_pro_monthly"
    STRIPE_ENTERPRISE_PRICE_ID: str = "price_enterprise_monthly"

    EMAIL_FROM: str = "noreply@example.com"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_BASE_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str | None = None
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_UPLOAD_TYPES: list[str] = [
        "image/png",
        "image/jpeg",
        "application/pdf",
        "text/csv",
    ]

    API_RATE_LIMIT_FREE: int = 60
    API_RATE_LIMIT_PRO: int = 500
    API_RATE_LIMIT_ENTERPRISE: int = 5000

    TOTP_ISSUER: str = "SaaS Boilerplate"
    WEBHOOK_SIGNING_SECRET: str = "local-webhook-secret"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
