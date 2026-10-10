"""One configuration source for the application and command-line tools."""

import secrets
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = {"change_me", "change_me_to_a_long_random_secret", "secret", "password"}


class Settings(BaseSettings):
    app_env: Literal["development", "production", "test"] = "development"
    demo_mode: bool = False
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "halva"
    db_user: str = "halva_user"
    db_password: str = ""
    admin_secret_key: str = ""
    admin_session_https_only: bool = False
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    delivery_price: Decimal = Field(
        default=Decimal("150.00"), ge=0, max_digits=10, decimal_places=2
    )
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = False
    smtp_starttls: bool = True
    email_from: str = ""
    orders_email: str = ""
    email_worker_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_environment(self):
        if self.smtp_use_ssl and self.smtp_starttls:
            raise ValueError("Choose SMTP_USE_SSL or SMTP_STARTTLS, not both")
        if self.app_env == "production":
            if self.demo_mode:
                raise ValueError("DEMO_MODE is for presentations; disable it in production")
            if self.database_url and not self.database_url.startswith(
                ("postgresql://", "postgresql+psycopg://")
            ):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if len(self.admin_secret_key) < 32 or self.admin_secret_key.lower() in PLACEHOLDERS:
                raise ValueError(
                    "Production needs a random ADMIN_SECRET_KEY of at least 32 characters"
                )
            if not self.admin_session_https_only:
                raise ValueError("Production needs ADMIN_SESSION_HTTPS_ONLY=true")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("Set ALLOWED_HOSTS to the actual production domains")
            if not self.database_url and (
                not self.db_password or self.db_password.lower() in PLACEHOLDERS
            ):
                raise ValueError("Production needs a real database password")
        if not self.admin_secret_key:
            # Local-only, ephemeral key. Set the environment variable to keep sessions across restarts.
            self.admin_secret_key = secrets.token_urlsafe(48)
        if self.email_worker_enabled:
            self.validate_smtp()
        return self

    def validate_smtp(self) -> None:
        if not all((self.smtp_host, self.smtp_username, self.smtp_password, self.orders_email)):
            raise ValueError("Configure SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and ORDERS_EMAIL")
        if not (self.smtp_use_ssl or self.smtp_starttls):
            raise ValueError("SMTP must use SSL or STARTTLS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
