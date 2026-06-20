from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, cast

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = Field("development", env="APP_ENV")
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    jwt_signing_key: str = Field(..., env="JWT_SIGNING_KEY")
    wix_hmac_secret: str = Field(..., env="WIX_HMAC_SECRET")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    s3_endpoint_url: Optional[str] = Field(None, env="S3_ENDPOINT_URL")
    s3_bucket: Optional[str] = Field(None, env="S3_BUCKET")
    s3_access_key: Optional[str] = Field(None, env="S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = Field(None, env="S3_SECRET_KEY")

    @property
    def config_dir(self) -> Path:
        """Path to the config directory."""
        return Path(__file__).parent.parent / "config"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


class _LazySettings:
    """Proxy that defers Settings instantiation until first attribute access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)


settings = cast(Settings, _LazySettings())
