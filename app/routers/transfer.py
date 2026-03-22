"""Transfer job endpoints — start a transfer, poll status, list jobs."""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import session_store
from app.database import AsyncSessionLocal, get_db
from app.models import BrowserSnapshot, EncryptedData, TransferJob
from app.routers.auth import get_current_user
from app.routers.billing import get_effective_tier, get_allowed_data_types
from app.schemas import TransferJobResponse, TransferRequest
from app.security import decrypt_data

router = APIRouter(prefix="/api/transfer", tags=["transfer"])


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _get_importer(browser: str, profile_path: Path):
    if browser in ("chrome", "edge", "brave"):
        from app.browsers.chrome import ChromiumImporter
        return ChromiumImporter(profile_path, browser=browser)
    if browser == "opera_gx":
        from app.browsers.opera_gx import OperaGXImporter
        return OperaGXImporter(profile_path)
    if browser == "firefox":
        from app.browsers.firefox import FirefoxImporter
        return FirefoxImporter(profile_path)
    raise ValueError(f"Unsupported browser: {browser}")


async def _run_transfer(job_id: int, jti: str) -> None:
    """Background task: decrypt source data and import into target browser."""
    from app.browsers.base import BrowserData, Bookmark, HistoryEntry, SavedPassword, Extension

    fernet = session_store.get_key(jti)

    async with AsyncSessionLocal() as db:
        job_result = await db.execute(select(TransferJob).where(TransferJob.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job or not fernet:
            return

        job.status = "running"
        await db.commit()

        try:
            # Load encrypted data from snapshot
            enc_result = await db.execute(
                select(EncryptedData).where(EncryptedData.snapshot_id == job.source_snapshot_id)
            )
            enc_rows = enc_result.scalars().all()

            data_types = json.loads(job.data_types)
            browser_data = BrowserData()

            type_map = {
                "bookmarks": (Bookmark, "bookmarks"),
                "history": (HistoryEntry, "history"),
                "passwords": (SavedPassword, "passwords"),
                "extensions": (Extension, "extensions"),
            }

            for row in enc_rows:
                if row.data_type not in data_types:
                    continue

                decrypted = decrypt_data(fernet, row.encrypted_blob)

                if row.data_type in type_map:
                    cls, attr = type_map[row.data_type]
                    items = [cls(**item) for item in decrypted]
                    setattr(browser_data, attr, items)
                elif row.data_type == "settings":
                    browser_data.settings = decrypted if isinstance(decrypted, dict) else {}

            # Import into target
            profile_path = Path(job.target_profile)
            if not profile_path.exists():
                raise FileNotFoundError(f"Target profile not found: {profile_path}")

            importer = _get_importer(job.target_browser, profile_path)
            summary = importer.import_data(browser_data, data_types)

            job.status = "done"
            job.result_summary = json.dumps(summary)
            job.completed_at = datetime.now(timezone.utc)

        except Exception as exc:
            job.status = "error"
            job.error_message = str(exc)[:512]
            job.completed_at = datetime.now(timezone.utc)

        await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=TransferJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_transfer(
    body: TransferRequest,
    background_tasks: BackgroundTasks,
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, jti = user_jti
    fernet = session_store.get_key(jti)
    if not fernet:
        raise HTTPException(status_code=401, detail="Session expired")

    # Enforce subscription tier
    allowed = get_allowed_data_types(get_effective_tier(user))
    locked = [t for t in body.data_types if t not in allowed]
    if locked:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan does not include: {', '.join(locked)}. Upgrade to Pro or Premium.",
        )

    # Verify snapshot belongs to this user
    snap_result = await db.execute(
        select(BrowserSnapshot).where(
            BrowserSnapshot.id == body.source_snapshot_id,
            BrowserSnapshot.user_id == user.id,
            BrowserSnapshot.status == "ready",
        )
    )
    snapshot = snap_result.scalar_one_or_none()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found or not ready")

    # Validate target profile path
    target_path = Path(body.target_profile)
    resolved = target_path.resolve()
    home = Path.home().resolve()
    if not str(resolved).startswith(str(home)):
        import os
        local_app = Path(os.environ.get("LOCALAPPDATA", str(home))).resolve()
        if not str(resolved).startswith(str(local_app)):
            raise HTTPException(status_code=400, detail="Target profile path is outside allowed directories")

    if not resolved.exists():
        raise HTTPException(status_code=400, detail="Target profile path does not exist")

    job = TransferJob(
        user_id=user.id,
        source_snapshot_id=body.source_snapshot_id,
        target_browser=body.target_browser,
        target_profile=str(resolved),
        data_types=json.dumps(body.data_types),
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    background_tasks.add_task(_run_transfer, job.id, jti)

    return job


@router.get("/status/{job_id}", response_model=TransferJobResponse)
async def transfer_status(
    job_id: int,
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, _ = user_jti
    result = await db.execute(
        select(TransferJob).where(TransferJob.id == job_id, TransferJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs", response_model=List[TransferJobResponse])
async def list_jobs(
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, _ = user_jti
    result = await db.execute(
        select(TransferJob).where(TransferJob.user_id == user.id)
        .order_by(TransferJob.created_at.desc())
    )
    return result.scalars().all()
