"""Application settings, loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LUMINA_", extra="ignore")

    # Google OAuth (Photos Library API, read-only). Obtain these by following
    # docs/GOOGLE_CLOUD_SETUP.md.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/google/callback"

    # Scoring
    sharpness_threshold: float = 150.0

    # Fetching remote images
    max_image_bytes: int = 25 * 1024 * 1024
    fetch_timeout_seconds: float = 20.0

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
