from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Set these via env vars or a .env file:
        ATHENA_CONFIG_PATH            -- path to the JSON config file (required for projection)
        ATHENA_CORS_ORIGINS           -- comma-separated allowed origins
        ATHENA_DATABASE_URL           -- PostgreSQL connection string
        ATHENA_JWT_SECRET             -- secret for signing auth tokens
        ATHENA_DISCORD_CLIENT_ID      -- Discord OAuth2 application client ID
        ATHENA_DISCORD_CLIENT_SECRET  -- Discord OAuth2 application client secret
        ATHENA_DISCORD_REDIRECT_URI   -- OAuth2 callback URL
        ATHENA_FRONTEND_URL           -- frontend origin for post-login redirect
        ATHENA_GOOGLE_CLIENT_ID       -- Google OAuth2 client ID (Gmail API)
        ATHENA_GOOGLE_CLIENT_SECRET   -- Google OAuth2 client secret
        ATHENA_GOOGLE_REFRESH_TOKEN   -- Gmail API refresh token (offline access)
        ATHENA_GOOGLE_PROJECT_ID      -- GCP project ID (for Pub/Sub topic)
        ATHENA_GOOGLE_PUSH_AUDIENCE   -- OIDC audience for Pub/Sub push verification
    """

    # Projection (file-based, pre-DB fallback)
    config_path: Path = Path("data.json")
    cors_origins: list[str] = ["http://localhost:5173"]
    debug: bool = False

    # Database
    database_url: str | None = None

    # Auth
    jwt_secret: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = ""
    frontend_url: str = "http://localhost:5173"

    # Gmail / Google Pub/Sub
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_project_id: str = ""
    google_push_audience: str = ""

    @property
    def secure_cookies(self) -> bool:
        """True when frontend is served over HTTPS (i.e. not local dev)."""
        return not self.frontend_url.startswith("http://localhost")

    model_config = {"env_prefix": "ATHENA_"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Dependency-injectable settings factory, cached for the process lifetime."""
    return Settings()
