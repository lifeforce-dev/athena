from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Set these via env vars or a .env file:
        ATHENA_CORS_ORIGINS           -- comma-separated allowed origins
        ATHENA_DATABASE_URL           -- PostgreSQL connection string
        ATHENA_JWT_SECRET             -- secret for signing auth tokens
        ATHENA_DISCORD_CLIENT_ID      -- Discord OAuth2 application client ID
        ATHENA_DISCORD_CLIENT_SECRET  -- Discord OAuth2 application client secret
        ATHENA_DISCORD_REDIRECT_URI   -- OAuth2 callback URL
        ATHENA_FRONTEND_URL           -- frontend origin for post-login redirect
        ATHENA_TELLER_APP_ID          -- Teller application ID
        ATHENA_TELLER_ENVIRONMENT     -- sandbox | development | production
        ATHENA_TELLER_WEBHOOK_SECRET  -- HMAC signing secret for webhook verification
        ATHENA_TELLER_ENCRYPTION_KEY  -- Fernet key for encrypting access tokens
        ATHENA_TELLER_CERTIFICATE_B64 -- base64-encoded mTLS client certificate
        ATHENA_TELLER_PRIVATE_KEY_B64 -- base64-encoded mTLS private key
        ATHENA_TELLER_TOKEN_SIGNING_KEY -- Ed25519 public key (base64) for enrollment verification
    """

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

    # Teller bank integration
    teller_app_id: str = ""
    teller_environment: str = "sandbox"
    teller_webhook_secret: str = ""
    teller_encryption_key: str = ""
    teller_certificate_b64: str = ""
    teller_private_key_b64: str = ""
    teller_token_signing_key: str = ""

    @property
    def secure_cookies(self) -> bool:
        """True when frontend is served over HTTPS (i.e. not local dev)."""
        return not self.frontend_url.startswith("http://localhost:")

    model_config = {"env_prefix": "ATHENA_"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Dependency-injectable settings factory, cached for the process lifetime."""
    return Settings()
