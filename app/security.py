"""Cryptographic utilities — key derivation, encryption, password hashing, JWT."""
import base64
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import JWTError, jwt

from app.config import settings


# ---------------------------------------------------------------------------
# Salt generation
# ---------------------------------------------------------------------------

def generate_salt() -> str:
    """Generate a 32-byte random salt, returned as a hex string for DB storage."""
    return secrets.token_hex(32)


# ---------------------------------------------------------------------------
# PBKDF2 key derivation (never stored on disk)
# ---------------------------------------------------------------------------

def derive_fernet(password: str, salt_hex: str) -> Fernet:
    """
    Derive a Fernet key from the user's master password and their stored salt.

    Uses PBKDF2-HMAC-SHA256 with 480,000 iterations (OWASP 2023 recommendation).
    The derived key exists only in memory; it is never written to disk or DB.
    """
    salt = bytes.fromhex(salt_hex)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=settings.pbkdf2_iterations,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return Fernet(key)


# ---------------------------------------------------------------------------
# Data encryption / decryption
# ---------------------------------------------------------------------------

def encrypt_data(fernet: Fernet, data: dict | list) -> str:
    """Encrypt a Python dict/list to a Fernet token string."""
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return fernet.encrypt(plaintext).decode("ascii")


def decrypt_data(fernet: Fernet, token: str) -> dict | list:
    """Decrypt a Fernet token string back to a Python object."""
    try:
        plaintext = fernet.decrypt(token.encode("ascii"))
        return json.loads(plaintext.decode("utf-8"))
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Decryption failed — wrong password or corrupted data.") from exc


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with bcrypt (cost factor from settings)."""
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.bcrypt_rounds),
    )
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, username: str) -> tuple[str, str]:
    """
    Create a signed JWT.

    Returns (token, jti) where jti is used as the key in the session store
    to associate the token with the in-memory Fernet key.
    """
    jti = secrets.token_hex(16)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns the payload dict or None if invalid."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
