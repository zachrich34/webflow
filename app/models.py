"""SQLAlchemy ORM models."""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, func
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    # bcrypt hash — never plaintext
    password_hash = Column(String(128), nullable=False)
    # 32 random bytes hex-encoded — used for PBKDF2 key derivation
    encryption_salt = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    # Subscription — "free" | "pro" | "premium"
    subscription_tier = Column(String(16), nullable=False, default="free", server_default="free")
    subscription_expires = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String(64), nullable=True, index=True)
    stripe_subscription_id = Column(String(64), nullable=True)

    snapshots = relationship("BrowserSnapshot", back_populates="user", cascade="all, delete-orphan")
    transfer_jobs = relationship("TransferJob", back_populates="user", cascade="all, delete-orphan")


class BrowserSnapshot(Base):
    """A captured snapshot of browser data for one profile."""
    __tablename__ = "browser_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    browser_name = Column(String(64), nullable=False)   # e.g. "chrome"
    profile_name = Column(String(128), nullable=False)  # e.g. "Default"
    os_platform = Column(String(32), nullable=False)    # linux | darwin | win32
    status = Column(String(16), default="pending")      # pending | ready | error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="snapshots")
    encrypted_data = relationship("EncryptedData", back_populates="snapshot", cascade="all, delete-orphan")


class EncryptedData(Base):
    """One row per data-type per snapshot. Blob is Fernet-encrypted JSON."""
    __tablename__ = "encrypted_data"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("browser_snapshots.id"), nullable=False)
    # bookmarks | history | passwords | extensions | settings
    data_type = Column(String(32), nullable=False)
    # Fernet token (base64url) — decryptable only with user's derived key
    encrypted_blob = Column(Text, nullable=False)
    item_count = Column(Integer, default=0)

    snapshot = relationship("BrowserSnapshot", back_populates="encrypted_data")


class TransferJob(Base):
    """Records a transfer from a snapshot to a destination browser."""
    __tablename__ = "transfer_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_snapshot_id = Column(Integer, ForeignKey("browser_snapshots.id"), nullable=False)
    target_browser = Column(String(64), nullable=False)
    target_profile = Column(String(128), nullable=False)
    # JSON list: ["bookmarks", "history", "passwords", "extensions", "settings"]
    data_types = Column(Text, nullable=False)
    status = Column(String(16), default="pending")  # pending | running | done | error
    # JSON dict: {"bookmarks": 42, "history": 1500, ...}
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="transfer_jobs")
