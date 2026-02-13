from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Set these via env vars or a .env file:
        ATHENA_CONFIG_PATH  -- path to the JSON config file (required for projection)
        ATHENA_CORS_ORIGINS -- comma-separated allowed origins (default: localhost dev server)
    """

    config_path: Path = Path("data.json")
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "ATHENA_"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Dependency-injectable settings factory, cached for the process lifetime."""
    return Settings()
