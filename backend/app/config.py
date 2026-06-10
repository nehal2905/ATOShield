"""Application configuration via pydantic-settings (reads .env).

No secrets live in code. Everything tunable — including the risk-tier
thresholds and the alert cutoff — is here so it can change without code edits
(the report's "configurable thresholds" requirement).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Database / cache
    database_url: str = "sqlite+aiosqlite:///./atoshield.db"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin"

    # ML artifacts
    ml_artifacts_dir: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "ml", "artifacts")
    )

    # Risk tiers (inclusive lower bounds) + alert threshold
    risk_medium_min: int = 25
    risk_high_min: int = 50
    risk_critical_min: int = 75
    alert_threshold: int = 60

    # Rate limits (slowapi syntax)
    rate_limit_events: str = "60/minute"
    rate_limit_simulate: str = "30/minute"

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def ml_dir(self) -> str:
        return os.path.dirname(self.ml_artifacts_dir.rstrip("/\\"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
