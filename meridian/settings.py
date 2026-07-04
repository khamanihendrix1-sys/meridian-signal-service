from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/meridian"
    redis_url: str = "redis://localhost:6379/0"
    jwt_signing_key: str = "dev-signing-key"
    log_level: str = "INFO"
    signal_scheduler_concurrency: int = 3
    celery_worker_concurrency: int = 4
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    cache_enabled: bool = True
    cache_prefix: str = "meridian:api"
    cache_default_ttl: int = 120
    cache_warm_on_startup: bool = True
    cache_ttl_listings_list: int = 120
    cache_ttl_listing_detail: int = 300
    cache_ttl_market_reports_list: int = 300
    cache_ttl_market_report_latest: int = 900
    cache_ttl_market_report_detail: int = 1800
    cache_ttl_signal_definitions: int = 3600
    cache_ttl_signal_logs: int = 120
    cache_ttl_comp_job: int = 60
    cache_ttl_overview: int = 60

    # CORS — comma-separated list of allowed origins.
    # Defaults to permissive ("*") in development; must be set explicitly in
    # production to a comma-separated list of exact origin URLs.
    cors_allowed_origins: str = "*"
    cors_allow_credentials: bool = False

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 200
    rate_limit_window_seconds: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        """Return the parsed list of allowed CORS origins."""
        raw = self.cors_allowed_origins.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def config_dir(self) -> Path:
        """Path to the config directory."""
        return Path(__file__).parent.parent / "config"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


class _LazySettings:
    """Proxy that defers Settings instantiation until first attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return getattr(get_settings(), name)
        except AttributeError as exc:
            raise AttributeError(
                f"'settings' object has no attribute {name!r}"
            ) from exc


settings = cast(Settings, _LazySettings())
