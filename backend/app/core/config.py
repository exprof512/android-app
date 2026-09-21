"""Environment-backed application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never authenticate a real deployment.
_PLACEHOLDER_SECRETS = frozenset({"change_me", "changeme", "placeholder", "secret"})
# RFC 7518 3.2 minimum for HMAC-SHA256 signing keys.
JWT_SECRET_MIN_LENGTH = 32


class Settings(BaseSettings):
    """Configuration only; values are never logged."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    database_url: str = ""
    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = ""
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_days: int = 30
    password_hasher: str = "argon2id"

    openai_api_key: str = ""
    openai_text_model: str = ""
    openai_text_timeout_seconds: int = 30
    openai_text_max_attempts: int = 2
    openai_image_model: str = "gpt-image-2"
    openai_image_size: str = ""
    openai_image_quality: str = ""
    openai_image_format: str = "webp"
    openai_image_timeout_seconds: int = 60
    image_max_retries: int = 3
    image_max_concurrent_jobs: int | None = None

    s3_provider: str = "minio"
    s3_endpoint: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "foodai-images"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_use_ssl: bool = False
    media_public_base_url: str = "http://localhost:8080/media"
    s3_presigned_url_ttl_seconds: int = 300
    minio_root_user: str = ""
    minio_root_password: str = ""

    nutrition_min_daily_calories_female: int = 1200
    nutrition_min_daily_calories_male: int = 1500
    nutrition_max_weekly_weight_change_kg: float | None = None
    nutrition_activity_factors_json: str = ""
    ai_cache_ttl_seconds: int = 86400
    ai_rate_limit_free_per_day: int | None = None
    ai_rate_limit_premium_per_day: int | None = None

    @field_validator("api_prefix")
    @classmethod
    def api_prefix_has_no_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator(
        "image_max_concurrent_jobs",
        "nutrition_max_weekly_weight_change_kg",
        "ai_rate_limit_free_per_day",
        "ai_rate_limit_premium_per_day",
        mode="before",
    )
    @classmethod
    def empty_optional_values_are_none(cls, value: object) -> object:
        return None if value == "" else value

    def required_runtime_settings(self) -> tuple[str, ...]:
        """Return missing dependencies without exposing their values."""
        required = {
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "JWT_SECRET": self.jwt_secret,
        }
        return tuple(name for name, value in required.items() if not value)

    def weak_runtime_settings(self) -> tuple[str, ...]:
        """Return secrets that are a sample value or too short, without exposing them."""
        weak: list[str] = []
        secret = self.jwt_secret.strip()
        if secret.lower() in _PLACEHOLDER_SECRETS or (
            secret and len(secret) < JWT_SECRET_MIN_LENGTH
        ):
            weak.append("JWT_SECRET")
        return tuple(weak)


@lru_cache
def get_settings() -> Settings:
    return Settings()
