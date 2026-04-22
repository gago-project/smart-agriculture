"""Typed environment settings for the Python Agent runtime."""

from __future__ import annotations


from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values read from `.env` or process environment."""

    app_env: str = "dev"
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "smart_agriculture"
    mysql_user: str = "smart_agriculture"
    mysql_password: str = "smart_agriculture_pwd"
    redis_url: str = "redis://redis:6379/0"
    qwen_api_key: str = ""
    debug_enabled: bool = False
    session_context_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings so callers do not repeatedly parse environment."""
    return Settings()
