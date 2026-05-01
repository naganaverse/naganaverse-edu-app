"""
config/config.py
─────────────────────────────────────────────────────────────
Centralised configuration using pydantic-settings.
All settings are loaded from environment variables / .env file.
─────────────────────────────────────────────────────────────
"""

from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # ... your existing variables (BOT_TOKEN, DATABASE_URL, etc.) ...

    # ── Notion Integration ────────────────────────────────
    # Add these three lines specifically:
    NOTION_TOKEN: str = ""
    NOTION_DATABASE_ID: str = ""
    NOTION_PASSKEY: str = "fallback_passkey" # This was missing

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ── Telegram ──────────────────────────────────────────
    BOT_TOKEN: str
    BOT_USERNAME: str = "naganaverse_bot"
    SUPER_ADMIN_IDS: str = ""  # raw comma-separated string

    @property
    def super_admin_id_list(self) -> List[int]:
        """Returns parsed list of super admin Telegram IDs."""
        if not self.SUPER_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.SUPER_ADMIN_IDS.split(",") if x.strip()]

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # ── Security ──────────────────────────────────────────
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days
    BCRYPT_ROUNDS: int = 12

    # ── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Brute Force Protection ────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30

    # ── AI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── File Storage ──────────────────────────────────────
    STORAGE_ENDPOINT: str = ""
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_BUCKET: str = "naganaverse-files"
    STORAGE_PUBLIC_URL: str = ""

    # ── Celery ────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Scheduler ─────────────────────────────────────────
    SCHEDULER_TIMEZONE: str = "Asia/Kolkata"

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/naganaverse.log"

    # ── Environment ───────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ── Subscription Plans ────────────────────────────────
    PLAN_BASIC_PRICE: int = 199
    PLAN_PRO_PRICE: int = 399
    PLAN_ENTERPRISE_PRICE: int = 699

    # ── Referral ──────────────────────────────────────────
    REFERRAL_DISCOUNT_PERCENT: int = 5

    # ── Monitoring ────────────────────────────────────────
    PROMETHEUS_PORT: int = 9090

    # ── Derived helpers ───────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton of Settings.
    Import this anywhere in the project:
        from config.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Convenience singleton — use this in most files
settings = get_settings()
