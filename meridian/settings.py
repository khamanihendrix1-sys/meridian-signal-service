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
