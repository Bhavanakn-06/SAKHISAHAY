"""Application configuration settings using Pydantic Settings."""

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Meta
    APP_NAME: str = "SAKHISAHAY API"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-replace-with-64-random-chars-in-production-must-be-very-long",
        description="HMAC secret key for JWT signing",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sakhisahay_db"
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_MIN_POOL_SIZE: int = 5
    MONGODB_TIMEOUT_MS: int = 5000

    # CORS & Hosts
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    )
    ALLOWED_HOSTS: str = "localhost,127.0.0.1,testserver"

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "5/minute"

    # Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 5
    ALLOWED_UPLOAD_TYPES: str = "image/png,image/jpeg,application/pdf"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    SMTP_TLS: bool = True

    # Email aliases & notification controls
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    SOS_ALERT_EMAIL: str = "damruthakalyani@gmail.com"
    ENABLE_REAL_NOTIFICATIONS: bool = True
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Seed Admin
    FIRST_ADMIN_EMAIL: str = "admin@sakhisahay.example"
    FIRST_ADMIN_PASSWORD: str = "AdminSecurePassword2026!"
    FIRST_ADMIN_NAME: str = "System Administrator"

    # Observability
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def allowed_upload_types_list(self) -> list[str]:
        return [
            t.strip().lower() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()
        ]

    @property
    def sos_alert_recipients(self) -> list[str]:
        raw = self.SOS_ALERT_EMAIL or ""
        return [email.strip() for email in raw.split(",") if email.strip() and "@" in email]

    @model_validator(mode="after")
    def validate_production_guards(self) -> "Settings":
        # Synchronize email aliases
        if self.EMAIL_USER and not self.SMTP_USER:
            self.SMTP_USER = self.EMAIL_USER
        elif self.SMTP_USER and not self.EMAIL_USER:
            self.EMAIL_USER = self.SMTP_USER

        if self.EMAIL_PASSWORD and not self.SMTP_PASSWORD:
            self.SMTP_PASSWORD = self.EMAIL_PASSWORD
        elif self.SMTP_PASSWORD and not self.EMAIL_PASSWORD:
            self.EMAIL_PASSWORD = self.SMTP_PASSWORD

        if not self.EMAIL_FROM:
            self.EMAIL_FROM = self.SMTP_USER or self.EMAIL_USER or "no-reply@sakhisahay.org"

        if self.ADMIN_EMAIL:
            self.FIRST_ADMIN_EMAIL = self.ADMIN_EMAIL
        elif self.FIRST_ADMIN_EMAIL:
            self.ADMIN_EMAIL = self.FIRST_ADMIN_EMAIL

        """Strict production guards: reject unsafe defaults when APP_ENV is production."""
        if self.APP_ENV == "production":
            if "dev-insecure" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "In production, SECRET_KEY must be a cryptographically strong secret of at least 32 characters."
                )
            if self.DEBUG:
                raise ValueError("DEBUG must be set to False in production.")
            if "*" in self.cors_origins_list:
                raise ValueError(
                    "CORS_ORIGINS cannot contain wildcards (*) in production."
                )
        return self


settings = Settings()
