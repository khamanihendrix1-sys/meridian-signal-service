from __future__ import annotations

from pathlib import Path
from typing import Optional

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


settings = Settings()
