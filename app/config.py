"""Application configuration from environment variables."""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "MantaQC"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    EXTERNAL_IP: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/quality_control"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_SECRET: Optional[str] = None

    # S3/MinIO
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "quality-control"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Bitrix Integration
    BITRIX_MODE: str = "stub"  # stub or live
    BITRIX_BASE_URL: Optional[str] = "https://b24-ea941g.bitrix24.by/rest/1/mjxechzjvf5d8c4g/"
    BITRIX_ACCESS_TOKEN: Optional[str] = None  # optional when using webhook-style authentication
    BITRIX_WEBHOOK_SECRET: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text

    # Timezone
    TIMEZONE: str = "UTC"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

