from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Runtime settings for the API process (env-overridable)."""

    model_config = SettingsConfigDict(env_prefix="CASHSIM_", case_sensitive=False)

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    allow_cors: bool = False
    cors_allow_origins: str = "*"
