"""Application configuration via environment variables / .env file."""
import os
import secrets
from pydantic_settings import BaseSettings


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

    # Database
    database_url: str = "sqlite+aiosqlite:///./webflow.db"

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
