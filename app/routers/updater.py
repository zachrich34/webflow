"""Auto-updater — checks GitHub releases, downloads & swaps the binary."""
import asyncio
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/update", tags=["update"])

GITHUB_REPO = "zachrich34/webflow"
GITHUB_API  = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
IS_FROZEN   = getattr(sys, "frozen", False)   # True only inside PyInstaller bundle

# ---------------------------------------------------------------------------
# In-memory state (single-process desktop app, no persistence needed)
# ---------------------------------------------------------------------------

_state: dict = {
    "status":         "idle",   # idle|checking|available|up_to_date|downloading|ready|error
    "latest_version": None,
    "download_url":   None,
    "download_path":  None,
    "progress":       0,
    "error":          None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_exe() -> Path:
    return Path(sys.executable if IS_FROZEN else sys.argv[0])


def _asset_name() -> str:
    return "WebFlow.exe" if platform.system() == "Windows" else "WebFlow"


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "WebFlow-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _do_check() -> dict:
    """Blocking — run in executor."""
    try:
        data = _fetch_json(GITHUB_API)
    except Exception as exc:
        return {"error": str(exc)}

    latest_tag = data.get("tag_name", "")
    latest_ver = latest_tag.lstrip("v")
    current_ver = settings.VERSION

    if _parse_version(latest_ver) <= _parse_version(current_ver):
        return {"up_to_date": True}

    # Find the matching release asset
    asset_name = _asset_name()
    download_url = None
    for asset in data.get("assets", []):
        if asset["name"].lower() == asset_name.lower():
            download_url = asset["browser_download_url"]
            break

    if not download_url:
        return {"error": f"Asset '{asset_name}' not found in release {latest_tag}"}

    return {
        "latest_version": latest_ver,
        "download_url":   download_url,
    }


def _do_download(url: str, dest: Path) -> None:
    """Blocking — run in executor."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "WebFlow-Updater/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(65_536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    _state["progress"] = int(downloaded * 100 / total)
    # Make executable on Unix
    if platform.system() != "Windows":
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _bg_check() -> None:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_check)

    if "error" in result:
        _state.update({"status": "idle", "error": result["error"]})
    elif result.get("up_to_date"):
        _state["status"] = "up_to_date"
    else:
        _state.update({
            "status":         "available",
            "latest_version": result["latest_version"],
            "download_url":   result["download_url"],
        })


async def _bg_download() -> None:
    url  = _state["download_url"]
    dest = Path(tempfile.gettempdir()) / "webflow_update" / _asset_name()
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _do_download, url, dest)
        _state.update({"status": "ready", "download_path": str(dest), "progress": 100})
    except Exception as exc:
        _state.update({"status": "error", "error": str(exc)})


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/check")
async def check_update():
    """Trigger a GitHub release check (non-blocking)."""
    if _state["status"] in ("checking", "downloading", "ready"):
        return _state
    _state.update({"status": "checking", "error": None})
    asyncio.create_task(_bg_check())
    return {"status": "checking"}


@router.get("/status")
async def get_status():
    return {
        "status":         _state["status"],
        "latest_version": _state["latest_version"],
        "current_version": settings.VERSION,
        "progress":       _state["progress"],
        "error":          _state["error"],
        "is_frozen":      IS_FROZEN,
    }


@router.post("/download")
async def start_download():
    if _state["status"] != "available":
        return {"ok": False, "msg": "No update available"}
    _state.update({"status": "downloading", "progress": 0, "error": None})
    asyncio.create_task(_bg_download())
    return {"ok": True}


@router.post("/apply")
async def apply_update():
    """Swap binaries and relaunch. Only works in frozen (packaged) mode."""
    if _state["status"] != "ready":
        return {"ok": False, "msg": "Download not complete"}
    if not IS_FROZEN:
        return {"ok": False, "msg": "Not running as packaged binary — update manually"}

    new_bin     = Path(_state["download_path"])
    current_bin = _current_exe()
    system      = platform.system()

    asyncio.create_task(_bg_apply(new_bin, current_bin, system))
    return {"ok": True}


async def _bg_apply(new_bin: Path, current_bin: Path, system: str) -> None:
    await asyncio.sleep(0.4)   # Let the HTTP response reach the client first

    if system == "Windows":
        # Can't overwrite a running .exe — use a helper batch script
        bat = Path(tempfile.gettempdir()) / "webflow_update.bat"
        bat.write_text(
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'copy /y "{new_bin}" "{current_bin}"\r\n'
            f'start "" "{current_bin}"\r\n'
            "del \"%~f0\"\r\n"
        )
        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        # Unix: replace in-place (running process keeps its fd open — safe)
        shutil.copy2(str(new_bin), str(current_bin))
        current_bin.chmod(current_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        subprocess.Popen([str(current_bin)])

    os._exit(0)
