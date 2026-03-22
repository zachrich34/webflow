"""Application configuration via environment variables / .env file."""
import os
import sys
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings


def _default_db_url() -> str:
    """Return a persistent database path that survives PyInstaller re-extractions."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "WebFlow"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "WebFlow"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "WebFlow"
    base.mkdir(parents=True, exist_ok=True)
    return "sqlite+aiosqlite:///" + (base / "webflow.db").as_posix()


class Settings(BaseSettings):
    # Security
    secret_key: str = os.environ.get("WEBFLOW_SECRET_KEY", secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Key derivation
    pbkdf2_iterations: int = 480_000  # OWASP 2023 minimum for PBKDF2-SHA256

    # Bcrypt
    bcrypt_rounds: int = 12

    # History limit (days)
    history_days: int = 90

    # Beta mode — all features unlocked for everyone, no paywall
    # Set WEBFLOW_BETA_MODE=false in .env when ready to enable paid tiers
    beta_mode: bool = True

    # Early adopter cutoff date (ISO format: "2025-06-01")
    # Users who registered before this date get lifetime premium automatically
    # Leave empty to disable
    early_adopter_cutoff: str = os.environ.get("WEBFLOW_EARLY_ADOPTER_CUTOFF", "")

    # Database
    database_url: str = _default_db_url()

    # Stripe (set in .env or environment variables)
    stripe_secret_key: str = os.environ.get("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_pro_price_id: str = os.environ.get("STRIPE_PRO_PRICE_ID", "")
    stripe_premium_price_id: str = os.environ.get("STRIPE_PREMIUM_PRICE_ID", "")
    # Base URL used for Stripe redirect URLs (must be publicly accessible for webhooks)
    app_base_url: str = os.environ.get("APP_BASE_URL", "http://localhost:8765")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
