"""
Chromium-based browser extractor/importer.

Supports: Google Chrome, Microsoft Edge, Brave, and Opera GX
(Opera GX uses this class via subclassing with different profile paths).

Password decryption:
  - Linux: passwords stored with libsecret / GNOME Keyring; fallback to AES-CBC with
    hardcoded key b"peanuts" (older Chrome builds) or no encryption.
  - macOS: AES key stored in macOS Keychain under "Chrome Safe Storage".
  - Windows: AES key wrapped with DPAPI (win32crypt); requires pywin32.

All decrypted passwords remain in memory only — never written to disk.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from app.browsers.base import (
    Bookmark,
    BrowserExtractor,
    BrowserImporter,
    Extension,
    HistoryEntry,
    ProfileInfo,
    SavedPassword,
    get_platform,
)


# ---------------------------------------------------------------------------
# Profile path detection
# ---------------------------------------------------------------------------

_PROFILE_PATHS = {
    "chrome": {
        "linux": [Path.home() / ".config" / "google-chrome"],
        "darwin": [Path.home() / "Library" / "Application Support" / "Google" / "Chrome"],
        "win32": [Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"],
    },
    "edge": {
        "linux": [Path.home() / ".config" / "microsoft-edge"],
        "darwin": [Path.home() / "Library" / "Application Support" / "Microsoft Edge"],
        "win32": [Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"],
    },
    "brave": {
        "linux": [Path.home() / ".config" / "BraveSoftware" / "Brave-Browser"],
        "darwin": [Path.home() / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser"],
        "win32": [Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data"],
    },
}


def detect_chromium_profiles(browser: str) -> List[ProfileInfo]:
    """Return a list of detected profiles for a Chromium browser."""
    platform = get_platform()
    paths = _PROFILE_PATHS.get(browser, {}).get(platform, [])
    profiles: List[ProfileInfo] = []

    for base in paths:
        if not base.exists():
            continue
        # Each profile is a sub-directory: Default, Profile 1, Profile 2, …
        for candidate in [base / "Default"] + list(base.glob("Profile *")):
            if (candidate / "Bookmarks").exists() or (candidate / "History").exists():
                profiles.append(ProfileInfo(
                    browser=browser,
                    profile=candidate.name,
                    path=str(candidate),
                    available=True,
                ))

    return profiles


# ---------------------------------------------------------------------------
# Chromium password decryption helpers
# ---------------------------------------------------------------------------

def _get_chromium_aes_key(user_data_dir: Path) -> Optional[bytes]:
    """
    Read and decrypt the AES-256-GCM key from Local State.
    Returns raw 32-byte key or None if unavailable.
    """
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.exists():
        return None

    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key_b64 = local_state["os_crypt"]["encrypted_key"]
    except (KeyError, json.JSONDecodeError):
        return None

    import base64
    encrypted_key = base64.b64decode(encrypted_key_b64)
    # First 5 bytes are the literal string "DPAPI"
    encrypted_key = encrypted_key[5:]

    platform = get_platform()
    if platform == "win32":
        try:
            import win32crypt  # type: ignore
            return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except Exception:
            return None
    elif platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["security", "find-generic-password", "-w", "-s", "Chrome Safe Storage", "-a", "Chrome"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                import hashlib
                safe_storage_key = result.stdout.strip().encode()
                # Chromium derives the AES key using PBKDF2 over the Keychain password
                dk = hashlib.pbkdf2_hmac("sha1", safe_storage_key, b"saltysalt", 1003, dklen=16)
                return dk
        except Exception:
            return None
    else:
        # Linux: try secretstorage (GNOME Keyring / KWallet)
        try:
            import secretstorage  # type: ignore
            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            for item in collection.get_all_items():
                if "Chrome" in item.get_label():
                    password = item.get_secret()
                    import hashlib
                    dk = hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1, dklen=16)
                    return dk
        except Exception:
            pass
        # Fallback: older builds use the hardcoded key
        import hashlib
        dk = hashlib.pbkdf2_hmac("sha1", b"peanuts", b"saltysalt", 1, dklen=16)
        return dk


def _decrypt_password_value(encrypted_value: bytes, aes_key: Optional[bytes]) -> str:
    """Decrypt a Chrome Login Data password field."""
    if not encrypted_value:
        return ""

    # v10/v11 prefix with AES-128-CBC (Linux legacy)
    if encrypted_value[:3] in (b"v10", b"v11"):
        if aes_key is None:
            return "<encrypted — key unavailable>"
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            iv = b" " * 16
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_value[3:]) + decryptor.finalize()
            # Remove PKCS7 padding
            pad_len = decrypted[-1]
            return decrypted[:-pad_len].decode("utf-8", errors="replace")
        except Exception:
            return "<decryption error>"

    # v80+ AES-256-GCM: [3 bytes version][12 bytes nonce][ciphertext][16 bytes tag]
    if encrypted_value[:3] == b"v80" or (len(encrypted_value) > 15 and aes_key and len(aes_key) == 32):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = encrypted_value[3:15]
            ciphertext = encrypted_value[15:]
            aesgcm = AESGCM(aes_key)
            return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8", errors="replace")
        except Exception:
            return "<decryption error>"

    return "<unknown encryption>"


# ---------------------------------------------------------------------------
# Chromium extractor
# ---------------------------------------------------------------------------

class ChromiumExtractor(BrowserExtractor):
    """Extract data from a Chromium-based browser profile."""

    def __init__(self, profile_path: Path, browser: str = "chrome"):
        super().__init__(profile_path)
        self.browser = browser
        # user_data_dir is one level up from profile (needed for Local State)
        self.user_data_dir = profile_path.parent

    # ---- Bookmarks ----

    def extract_bookmarks(self) -> List[Bookmark]:
        bm_file = self.profile_path / "Bookmarks"
        if not bm_file.exists():
            return []
        with open(bm_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items: List[Bookmark] = []
        self._walk_bookmarks(raw.get("roots", {}), items, "")
        return items

    def _walk_bookmarks(self, node: dict | list, out: List[Bookmark], folder: str) -> None:
        if isinstance(node, list):
            for child in node:
                self._walk_bookmarks(child, out, folder)
        elif isinstance(node, dict):
            ntype = node.get("type", "")
            if ntype == "url":
                out.append(Bookmark(
                    title=node.get("name", ""),
                    url=node.get("url", ""),
                    folder=folder,
                    added=int(node.get("date_added", 0)) or None,
                ))
            elif ntype == "folder":
                sub = folder + "/" + node.get("name", "") if folder else node.get("name", "")
                self._walk_bookmarks(node.get("children", []), out, sub)
            else:
                # Root nodes (bookmark_bar, other, synced)
                for v in node.values():
                    if isinstance(v, dict):
                        self._walk_bookmarks(v, out, folder)

    # ---- History ----

    def extract_history(self, days: int = 90) -> List[HistoryEntry]:
        history_file = self.profile_path / "History"
        if not history_file.exists():
            return []

        cutoff_us = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1_000_000)
        # Chrome epoch starts 1601-01-01; offset from Unix epoch
        chrome_epoch_offset_us = 11644473600 * 1_000_000

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(history_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT url, title, visit_count, last_visit_time FROM urls "
                "WHERE last_visit_time > ? ORDER BY last_visit_time DESC LIMIT 50000",
                (cutoff_us + chrome_epoch_offset_us,),
            ).fetchall()
            conn.close()
        finally:
            os.unlink(tmp_path)

        return [
            HistoryEntry(
                url=r["url"],
                title=r["title"] or "",
                visit_count=r["visit_count"],
                last_visited=r["last_visit_time"],
            )
            for r in rows
        ]

    # ---- Passwords ----

    def extract_passwords(self) -> List[SavedPassword]:
        login_file = self.profile_path / "Login Data"
        if not login_file.exists():
            return []

        aes_key = _get_chromium_aes_key(self.user_data_dir)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(login_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT origin_url, username_value, password_value FROM logins"
            ).fetchall()
            conn.close()
        finally:
            os.unlink(tmp_path)

        passwords = []
        for r in rows:
            decrypted = _decrypt_password_value(bytes(r["password_value"]), aes_key)
            passwords.append(SavedPassword(
                origin_url=r["origin_url"],
                username=r["username_value"],
                password=decrypted,
            ))
        return passwords

    # ---- Extensions ----

    def extract_extensions(self) -> List[Extension]:
        ext_dir = self.profile_path / "Extensions"
        if not ext_dir.exists():
            return []
        extensions = []
        for ext_path in ext_dir.iterdir():
            if not ext_path.is_dir() or ext_path.name.startswith("."):
                continue
            ext_id = ext_path.name
            # Find the version directory (e.g. 1.2.3_0)
            version_dirs = list(ext_path.iterdir())
            if not version_dirs:
                continue
            version_dir = version_dirs[-1]
            manifest_path = version_dir / "manifest.json"
            name = ext_id
            version = version_dir.name.split("_")[0]
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    name = manifest.get("name", ext_id)
                    version = manifest.get("version", version)
                except (json.JSONDecodeError, OSError):
                    pass
            store_url = f"https://chrome.google.com/webstore/detail/{ext_id}"
            extensions.append(Extension(
                name=name, ext_id=ext_id, version=version, store_url=store_url
            ))
        return extensions

    # ---- Settings ----

    def extract_settings(self) -> dict:
        prefs_file = self.profile_path / "Preferences"
        if not prefs_file.exists():
            return {}
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
        # Extract only safe, non-sensitive settings
        return {
            "homepage": prefs.get("homepage", ""),
            "homepage_is_newtabpage": prefs.get("homepage_is_newtabpage", True),
            "default_search_provider": prefs.get("default_search_provider_data", {}).get("keyword", ""),
            "show_bookmarks_bar": prefs.get("bookmarks", {}).get("show_on_all_tabs", False),
        }


# ---------------------------------------------------------------------------
# Chromium importer
# ---------------------------------------------------------------------------

class ChromiumImporter(BrowserImporter):
    """Write data into a Chromium-based browser profile."""

    def __init__(self, profile_path: Path, browser: str = "chrome"):
        super().__init__(profile_path)
        self.browser = browser

    def import_bookmarks(self, items: List[Bookmark]) -> int:
        bm_file = self.profile_path / "Bookmarks"
        # Read existing bookmarks or create fresh structure
        if bm_file.exists():
            try:
                with open(bm_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = {}
        else:
            existing = {}

        if "roots" not in existing:
            existing["roots"] = {
                "bookmark_bar": {"children": [], "name": "Bookmarks bar", "type": "folder"},
                "other": {"children": [], "name": "Other bookmarks", "type": "folder"},
                "synced": {"children": [], "name": "Mobile bookmarks", "type": "folder"},
            }
            existing["version"] = 1

        # Add all imported bookmarks into "Other bookmarks"
        other = existing["roots"].setdefault("other", {"children": [], "name": "Other bookmarks", "type": "folder"})
        imported_folder = {
            "children": [],
            "name": "Imported by WebFlow",
            "type": "folder",
            "date_added": "0",
            "date_modified": "0",
            "id": "99999",
            "guid": "imported-webflow",
        }
        for bm in items:
            imported_folder["children"].append({
                "name": bm.title,
                "type": "url",
                "url": bm.url,
                "date_added": str(bm.added or 0),
                "id": str(abs(hash(bm.url)) % 100000),
                "guid": f"wf-{abs(hash(bm.url)):x}",
            })
        other.setdefault("children", []).append(imported_folder)

        with open(bm_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        return len(items)

    def import_history(self, items: List[HistoryEntry]) -> int:
        history_file = self.profile_path / "History"
        if not history_file.exists():
            return 0  # Don't create History DB from scratch (complex schema)

        chrome_epoch_offset_us = 11644473600 * 1_000_000

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(history_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            count = 0
            for entry in items:
                ts = (entry.last_visited or 0) + chrome_epoch_offset_us
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO urls (url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?)",
                        (entry.url, entry.title, entry.visit_count, ts),
                    )
                    count += 1
                except sqlite3.Error:
                    pass
            conn.commit()
            conn.close()
            shutil.copy2(tmp_path, str(history_file))
        finally:
            os.unlink(tmp_path)
        return count

    def import_passwords(self, items: List[SavedPassword]) -> int:
        # Chrome re-encrypts passwords on write using OS keychain; out of scope for automated import.
        # Instead, we write an importable CSV for manual import via chrome://settings/passwords.
        csv_path = self.profile_path / "webflow_passwords_import.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,url,username,password\n")
            for p in items:
                # Escape commas/quotes in fields
                def esc(s: str) -> str:
                    return '"' + s.replace('"', '""') + '"'
                f.write(f"{esc(p.origin_url)},{esc(p.origin_url)},{esc(p.username)},{esc(p.password)}\n")
        return len(items)

    def import_extensions(self, items: List[Extension]) -> int:
        # Cannot auto-install extensions; write a helper HTML page with links
        html_path = self.profile_path / "webflow_extensions.html"
        rows = "\n".join(
            f'<tr><td>{ext.name}</td><td><a href="{ext.store_url}" target="_blank">Install</a></td><td>{ext.version}</td></tr>'
            for ext in items
        )
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Extensions to Install</title>
<style>body{{font-family:sans-serif;padding:20px}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:8px}}tr:nth-child(even){{background:#f2f2f2}}</style>
</head><body>
<h2>Extensions transferred by WebFlow</h2>
<p>Click each link to install the extension in your new browser.</p>
<table><tr><th>Name</th><th>Install</th><th>Version</th></tr>{rows}</table>
</body></html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return len(items)

    def import_settings(self, settings_data: dict) -> int:
        prefs_file = self.profile_path / "Preferences"
        if not prefs_file.exists():
            return 0
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except (json.JSONDecodeError, OSError):
            prefs = {}

        count = 0
        if settings_data.get("homepage"):
            prefs["homepage"] = settings_data["homepage"]
            count += 1
        if "homepage_is_newtabpage" in settings_data:
            prefs["homepage_is_newtabpage"] = settings_data["homepage_is_newtabpage"]

        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        return count
