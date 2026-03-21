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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
