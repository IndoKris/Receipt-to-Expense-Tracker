"""Application configuration and environment settings."""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env file."""

    gemini_api_key: Optional[str] = None
    gemma_model: Optional[str] = None
    app_token: str = "change-me"
    max_upload_mb: int = 6
    rate_limit_per_min: int = 20
    model_timeout_s: float = 40.0
    provider: str = "gemma"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def validate_provider(self) -> None:
        """Fail fast if provider is 'gemma' and required credentials are missing."""
        if self.provider.strip().lower() == "gemma":
            missing = []
            if not self.gemini_api_key or not self.gemini_api_key.strip():
                missing.append("GEMINI_API_KEY")
            if not self.gemma_model or not self.gemma_model.strip():
                missing.append("GEMMA_MODEL")
            if missing:
                raise ValueError(
                    f"PROVIDER is set to 'gemma' but required environment variable(s) "
                    f"are missing: {', '.join(missing)}. "
                    f"Please provide them in .env or set PROVIDER=fake for testing/development."
                )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
