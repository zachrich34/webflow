"""Opera GX browser extractor/importer (Chromium-based, custom profile paths)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from app.browsers.base import ProfileInfo, get_platform
from app.browsers.chrome import ChromiumExtractor, ChromiumImporter


_OPERA_GX_PATHS = {
    "linux": [Path.home() / ".config" / "opera"],
    "darwin": [Path.home() / "Library" / "Application Support" / "com.operasoftware.Opera"],
    "win32": [
        Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera GX Stable",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Opera GX",
    ],
}


def detect_opera_gx_profiles() -> List[ProfileInfo]:
    """Return detected Opera GX profiles."""
    platform = get_platform()
    paths = _OPERA_GX_PATHS.get(platform, [])
    profiles: List[ProfileInfo] = []

    for base in paths:
        if not base.exists():
            continue
        # Opera GX uses the base dir itself (no "User Data" sub-folder on Linux/Mac)
        if (base / "Bookmarks").exists() or (base / "History").exists():
            profiles.append(ProfileInfo(
                browser="opera_gx",
                profile="Default",
                path=str(base),
                available=True,
            ))
        # Also check "Default" sub-dir
        default = base / "Default"
        if default.exists() and ((default / "Bookmarks").exists() or (default / "History").exists()):
            profiles.append(ProfileInfo(
                browser="opera_gx",
                profile="Default",
                path=str(default),
                available=True,
            ))

    return profiles


class OperaGXExtractor(ChromiumExtractor):
    """Opera GX shares the Chromium data format; reuse ChromiumExtractor."""

    def __init__(self, profile_path: Path):
        super().__init__(profile_path, browser="opera_gx")
        # Opera GX stores Local State in the parent or the profile dir itself
        self.user_data_dir = profile_path.parent if (profile_path.parent / "Local State").exists() else profile_path


class OperaGXImporter(ChromiumImporter):
    """Opera GX shares the Chromium data format; reuse ChromiumImporter."""

    def __init__(self, profile_path: Path):
        super().__init__(profile_path, browser="opera_gx")
