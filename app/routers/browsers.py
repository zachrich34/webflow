"""Browser detection and snapshot endpoints."""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import session_store
from app.database import get_db
from app.models import BrowserSnapshot, EncryptedData
from app.routers.auth import get_current_user
from app.routers.billing import get_effective_tier, get_allowed_data_types
from app.schemas import BrowserProfile, DetectedBrowsers, SnapshotRequest, SnapshotResponse
from app.security import encrypt_data

router = APIRouter(prefix="/api/browsers", tags=["browsers"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_all_profiles() -> List[BrowserProfile]:
    """Auto-detect all installed browsers and their profiles."""
    from app.browsers.chrome import detect_chromium_profiles
    from app.browsers.firefox import detect_firefox_profiles
    from app.browsers.opera_gx import detect_opera_gx_profiles

    profiles: List[BrowserProfile] = []

    for browser in ("chrome", "edge", "brave"):
        for p in detect_chromium_profiles(browser):
            profiles.append(BrowserProfile(
                browser=p.browser, profile=p.profile, path=p.path, available=p.available
            ))

    for p in detect_opera_gx_profiles():
        profiles.append(BrowserProfile(
            browser=p.browser, profile=p.profile, path=p.path, available=p.available
        ))

    for p in detect_firefox_profiles():
        profiles.append(BrowserProfile(
            browser=p.browser, profile=p.profile, path=p.path, available=p.available
        ))

    return profiles


def _get_extractor(browser: str, profile_path: Path):
    if browser in ("chrome", "edge", "brave"):
        from app.browsers.chrome import ChromiumExtractor
        return ChromiumExtractor(profile_path, browser=browser)
    if browser == "opera_gx":
        from app.browsers.opera_gx import OperaGXExtractor
        return OperaGXExtractor(profile_path)
    if browser == "firefox":
        from app.browsers.firefox import FirefoxExtractor
        return FirefoxExtractor(profile_path)
    raise ValueError(f"Unsupported browser: {browser}")


def _get_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    return "win32"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/detect", response_model=DetectedBrowsers)
async def detect_browsers(user_jti: tuple = Depends(get_current_user)):
    profiles = _detect_all_profiles()
    return DetectedBrowsers(platform=_get_platform(), browsers=profiles)


@router.get("/profiles/{browser}", response_model=List[BrowserProfile])
async def list_profiles(browser: str, user_jti: tuple = Depends(get_current_user)):
    from app.browsers.chrome import detect_chromium_profiles
    from app.browsers.firefox import detect_firefox_profiles
    from app.browsers.opera_gx import detect_opera_gx_profiles

    if browser in ("chrome", "edge", "brave"):
        raw = detect_chromium_profiles(browser)
    elif browser == "opera_gx":
        raw = detect_opera_gx_profiles()
    elif browser == "firefox":
        raw = detect_firefox_profiles()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported browser: {browser}")

    return [BrowserProfile(browser=p.browser, profile=p.profile, path=p.path, available=p.available) for p in raw]


@router.post("/snapshot", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    body: SnapshotRequest,
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, jti = user_jti
    fernet = session_store.get_key(jti)
    if not fernet:
        raise HTTPException(status_code=401, detail="Session expired")

    # Enforce subscription tier — silently drop types the user's plan doesn't allow
    allowed = get_allowed_data_types(get_effective_tier(user))
    locked = [t for t in body.data_types if t not in allowed]
    if locked:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan does not include: {', '.join(locked)}. Upgrade to Pro or Premium.",
        )

    profile_path = Path(body.profile)
    if not profile_path.exists():
        raise HTTPException(status_code=400, detail="Profile path does not exist")

    # Validate that the profile path is inside an expected base directory
    # (prevent path traversal to arbitrary files)
    resolved = profile_path.resolve()
    home = Path.home().resolve()
    local_app = None
    try:
        import os
        local_app = Path(os.environ.get("LOCALAPPDATA", str(home))).resolve()
    except Exception:
        pass

    is_safe = str(resolved).startswith(str(home))
    if local_app:
        is_safe = is_safe or str(resolved).startswith(str(local_app))
    if not is_safe:
        raise HTTPException(status_code=400, detail="Profile path is outside allowed directories")

    snapshot = BrowserSnapshot(
        user_id=user.id,
        browser_name=body.browser,
        profile_name=resolved.name,
        os_platform=_get_platform(),
        status="pending",
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)

    try:
        extractor = _get_extractor(body.browser, resolved)
        from app.config import settings as cfg
        browser_data = extractor.extract_all(body.data_types, days=cfg.history_days)

        for dtype in body.data_types:
            raw_items = getattr(browser_data, dtype if dtype != "settings" else "settings", None)
            if raw_items is None:
                continue

            # Convert dataclasses to dicts
            if isinstance(raw_items, list):
                serializable = [dataclasses.asdict(item) for item in raw_items]
            else:
                serializable = raw_items  # dict (settings)

            encrypted_blob = encrypt_data(fernet, serializable)
            item_count = len(raw_items) if isinstance(raw_items, list) else len(raw_items)

            enc = EncryptedData(
                snapshot_id=snapshot.id,
                data_type=dtype,
                encrypted_blob=encrypted_blob,
                item_count=item_count,
            )
            db.add(enc)

        snapshot.status = "ready"
    except Exception as exc:
        snapshot.status = "error"
        snapshot.error_message = str(exc)[:512]

    await db.flush()
    await db.refresh(snapshot)

    # Build data_summary for response
    result = await db.execute(
        select(EncryptedData).where(EncryptedData.snapshot_id == snapshot.id)
    )
    enc_rows = result.scalars().all()
    data_summary = {row.data_type: row.item_count for row in enc_rows}

    return SnapshotResponse(
        id=snapshot.id,
        browser_name=snapshot.browser_name,
        profile_name=snapshot.profile_name,
        os_platform=snapshot.os_platform,
        status=snapshot.status,
        created_at=snapshot.created_at,
        data_summary=data_summary,
    )


@router.get("/snapshots", response_model=List[SnapshotResponse])
async def list_snapshots(
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, _ = user_jti
    result = await db.execute(
        select(BrowserSnapshot).where(BrowserSnapshot.user_id == user.id)
        .order_by(BrowserSnapshot.created_at.desc())
    )
    snapshots = result.scalars().all()

    out = []
    for snap in snapshots:
        enc_result = await db.execute(
            select(EncryptedData).where(EncryptedData.snapshot_id == snap.id)
        )
        enc_rows = enc_result.scalars().all()
        data_summary = {row.data_type: row.item_count for row in enc_rows}
        out.append(SnapshotResponse(
            id=snap.id,
            browser_name=snap.browser_name,
            profile_name=snap.profile_name,
            os_platform=snap.os_platform,
            status=snap.status,
            created_at=snap.created_at,
            data_summary=data_summary,
        ))
    return out
