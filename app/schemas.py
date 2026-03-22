"""Pydantic request/response schemas — all inputs validated before use."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-]{3,32}", v):
            raise ValueError("Username must be 3-32 characters: letters, digits, _ or -")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_strip(cls, v: str) -> str:
        return v.strip()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Browser snapshots
# ---------------------------------------------------------------------------

class SnapshotRequest(BaseModel):
    browser: str
    profile: str
    data_types: List[str]

    @field_validator("browser")
    @classmethod
    def browser_valid(cls, v: str) -> str:
        allowed = {"chrome", "firefox", "opera_gx", "edge", "brave"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"Unsupported browser. Allowed: {allowed}")
        return v

    @field_validator("data_types")
    @classmethod
    def types_valid(cls, v: List[str]) -> List[str]:
        allowed = {"bookmarks", "history", "passwords", "extensions", "settings"}
        for t in v:
            if t not in allowed:
                raise ValueError(f"Unknown data type '{t}'. Allowed: {allowed}")
        return v


class SnapshotResponse(BaseModel):
    id: int
    browser_name: str
    profile_name: str
    os_platform: str
    status: str
    created_at: datetime
    data_summary: Optional[dict] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Transfer jobs
# ---------------------------------------------------------------------------

class TransferRequest(BaseModel):
    source_snapshot_id: int
    target_browser: str
    target_profile: str
    data_types: List[str]

    @field_validator("target_browser")
    @classmethod
    def browser_valid(cls, v: str) -> str:
        allowed = {"chrome", "firefox", "opera_gx", "edge", "brave"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"Unsupported browser. Allowed: {allowed}")
        return v

    @field_validator("data_types")
    @classmethod
    def types_valid(cls, v: List[str]) -> List[str]:
        allowed = {"bookmarks", "history", "passwords", "extensions", "settings"}
        for t in v:
            if t not in allowed:
                raise ValueError(f"Unknown data type '{t}'.")
        return v


class TransferJobResponse(BaseModel):
    id: int
    source_snapshot_id: int
    target_browser: str
    target_profile: str
    data_types: str
    status: str
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Browser detection
# ---------------------------------------------------------------------------

class BrowserProfile(BaseModel):
    browser: str
    profile: str
    path: str
    available: bool


class DetectedBrowsers(BaseModel):
    platform: str
    browsers: List[BrowserProfile]
