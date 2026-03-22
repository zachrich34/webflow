"""
Firefox browser extractor/importer.

Bookmarks & history: read from places.sqlite (SQLite).
Passwords: read from logins.json; NSS decryption via ctypes (libnss3).
Extensions: read from extensions.json.
Settings: parse prefs.js.

NSS password decryption is complex and OS-dependent.
If NSS is unavailable we note the passwords as requiring manual export
(Firefox → Settings → Passwords → Export) and guide the user.
"""
from __future__ import annotations

import ctypes
import glob
import json
import os
import platform
import shutil
import sqlite3
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

def _firefox_base_dirs() -> List[Path]:
    platform_str = get_platform()
    if platform_str == "linux":
        return [Path.home() / ".mozilla" / "firefox"]
    if platform_str == "darwin":
        return [Path.home() / "Library" / "Application Support" / "Firefox" / "Profiles"]
    # Windows
    return [Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"]


def detect_firefox_profiles() -> List[ProfileInfo]:
    """Return all Firefox profiles found on the system."""
    profiles: List[ProfileInfo] = []
    for base in _firefox_base_dirs():
        if not base.exists():
            continue
        for candidate in base.iterdir():
            if not candidate.is_dir():
                continue
            if (candidate / "places.sqlite").exists():
                profiles.append(ProfileInfo(
                    browser="firefox",
                    profile=candidate.name,
                    path=str(candidate),
                    available=True,
                ))
    return profiles


# ---------------------------------------------------------------------------
# NSS password decryption (best-effort)
# ---------------------------------------------------------------------------

def _find_nss_library() -> Optional[str]:
    """Try to find libnss3 on the current system."""
    candidates = []
    p = get_platform()
    if p == "linux":
        candidates = [
            "/usr/lib/x86_64-linux-gnu/libnss3.so",
            "/usr/lib/libnss3.so",
            "/usr/lib64/libnss3.so",
        ]
    elif p == "darwin":
        candidates = [
            "/Applications/Firefox.app/Contents/MacOS/libnss3.dylib",
            "/usr/local/lib/libnss3.dylib",
        ]
    else:
        import winreg  # type: ignore
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Mozilla\Mozilla Firefox")
            path, _ = winreg.QueryValueEx(key, "Install Directory")
            candidates = [os.path.join(path, "nss3.dll")]
        except Exception:
            candidates = [r"C:\Program Files\Mozilla Firefox\nss3.dll"]

    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _nss_decrypt(profile_path: Path, encrypted_value: str) -> Optional[str]:
    """Attempt to decrypt a Firefox NSS-encrypted password value."""
    nss_path = _find_nss_library()
    if not nss_path:
        return None

    try:
        nss = ctypes.CDLL(nss_path)
        nss.NSS_Init(str(profile_path).encode("utf-8"))

        class SECItem(ctypes.Structure):
            _fields_ = [("type", ctypes.c_uint), ("data", ctypes.POINTER(ctypes.c_char)), ("len", ctypes.c_uint)]

        import base64
        decoded = base64.b64decode(encrypted_value)

        encrypted_item = SECItem()
        encrypted_item.data = ctypes.cast(ctypes.c_char_p(decoded), ctypes.POINTER(ctypes.c_char))
        encrypted_item.len = len(decoded)

        decrypted_item = SECItem()
        nss.PK11SDR_Decrypt(ctypes.byref(encrypted_item), ctypes.byref(decrypted_item), None)

        result = ctypes.string_at(decrypted_item.data, decrypted_item.len).decode("utf-8", errors="replace")
        nss.NSS_Shutdown()
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Firefox extractor
# ---------------------------------------------------------------------------

class FirefoxExtractor(BrowserExtractor):

    def extract_bookmarks(self) -> List[Bookmark]:
        db_file = self.profile_path / "places.sqlite"
        if not db_file.exists():
            return []

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(db_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT b.title, p.url, b.dateAdded,
                       (SELECT title FROM moz_bookmarks WHERE id = b.parent) AS folder
                FROM moz_bookmarks b
                JOIN moz_places p ON b.fk = p.id
                WHERE b.type = 1
                  AND p.url NOT LIKE 'place:%'
                ORDER BY b.dateAdded DESC
            """).fetchall()
            conn.close()
        finally:
            os.unlink(tmp_path)

        return [
            Bookmark(
                title=r["title"] or r["url"],
                url=r["url"],
                folder=r["folder"] or "",
                added=r["dateAdded"],
            )
            for r in rows
        ]

    def extract_history(self, days: int = 90) -> List[HistoryEntry]:
        db_file = self.profile_path / "places.sqlite"
        if not db_file.exists():
            return []

        # Firefox timestamps are in microseconds since Unix epoch
        cutoff_us = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1_000_000)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(db_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT p.url, p.title, p.visit_count, MAX(h.visit_date) AS last_visit
                FROM moz_places p
                JOIN moz_historyvisits h ON h.place_id = p.id
                WHERE h.visit_date > ?
                GROUP BY p.id
                ORDER BY last_visit DESC
                LIMIT 50000
            """, (cutoff_us,)).fetchall()
            conn.close()
        finally:
            os.unlink(tmp_path)

        return [
            HistoryEntry(
                url=r["url"],
                title=r["title"] or "",
                visit_count=r["visit_count"],
                last_visited=r["last_visit"],
            )
            for r in rows
        ]

    def extract_passwords(self) -> List[SavedPassword]:
        logins_file = self.profile_path / "logins.json"
        if not logins_file.exists():
            return []

        try:
            with open(logins_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        passwords = []
        for login in data.get("logins", []):
            enc_user = login.get("encryptedUsername", "")
            enc_pass = login.get("encryptedPassword", "")
            url = login.get("hostname", "")

            username = _nss_decrypt(self.profile_path, enc_user)
            password = _nss_decrypt(self.profile_path, enc_pass)

            if username is None or password is None:
                username = username or "<NSS unavailable — export manually>"
                password = password or "<NSS unavailable — export manually>"

            passwords.append(SavedPassword(origin_url=url, username=username, password=password))
        return passwords

    def extract_extensions(self) -> List[Extension]:
        ext_file = self.profile_path / "extensions.json"
        if not ext_file.exists():
            return []

        try:
            with open(ext_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        extensions = []
        for addon in data.get("addons", []):
            if addon.get("type") != "extension":
                continue
            ext_id = addon.get("id", "")
            name = addon.get("defaultLocale", {}).get("name", ext_id)
            version = addon.get("version", "")
            store_url = f"https://addons.mozilla.org/en-US/firefox/addon/{ext_id.replace('@', '').split('.')[0]}/"
            extensions.append(Extension(name=name, ext_id=ext_id, version=version, store_url=store_url))
        return extensions

    def extract_settings(self) -> dict:
        prefs_file = self.profile_path / "prefs.js"
        if not prefs_file.exists():
            return {}

        settings_out = {}
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith("user_pref("):
                        continue
                    # Parse: user_pref("key", value);
                    inner = line[len("user_pref("):-2]  # remove "user_pref(" and ");"
                    comma_idx = inner.index(",")
                    key = inner[:comma_idx].strip().strip('"')
                    value = inner[comma_idx + 1:].strip()
                    if key in ("browser.startup.homepage", "browser.search.defaultenginename",
                                "browser.toolbars.bookmarks.visibility"):
                        # Remove surrounding quotes if string
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        settings_out[key] = value
        except OSError:
            pass
        return settings_out


# ---------------------------------------------------------------------------
# Firefox importer
# ---------------------------------------------------------------------------

class FirefoxImporter(BrowserImporter):

    def import_bookmarks(self, items: List[Bookmark]) -> int:
        db_file = self.profile_path / "places.sqlite"
        if not db_file.exists():
            return 0

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(db_file), tmp_path)
            conn = sqlite3.connect(tmp_path)

            # Find or create an "Imported by WebFlow" folder under Unfiled Bookmarks
            row = conn.execute("SELECT id FROM moz_bookmarks WHERE title = 'Imported by WebFlow'").fetchone()
            if row:
                folder_id = row[0]
            else:
                parent_row = conn.execute(
                    "SELECT id FROM moz_bookmarks WHERE title = 'Other Bookmarks' OR title = 'Unfiled Bookmarks' LIMIT 1"
                ).fetchone()
                parent_id = parent_row[0] if parent_row else 1
                conn.execute(
                    "INSERT INTO moz_bookmarks (type, parent, title, dateAdded, lastModified) VALUES (2, ?, 'Imported by WebFlow', ?, ?)",
                    (parent_id, 0, 0),
                )
                folder_id = conn.lastrowid

            count = 0
            for bm in items:
                # Insert into moz_places
                existing = conn.execute("SELECT id FROM moz_places WHERE url = ?", (bm.url,)).fetchone()
                if existing:
                    place_id = existing[0]
                else:
                    conn.execute(
                        "INSERT INTO moz_places (url, title, visit_count) VALUES (?, ?, 0)",
                        (bm.url, bm.title),
                    )
                    place_id = conn.lastrowid

                conn.execute(
                    "INSERT INTO moz_bookmarks (type, fk, parent, title, dateAdded, lastModified) VALUES (1, ?, ?, ?, ?, ?)",
                    (place_id, folder_id, bm.title, bm.added or 0, bm.added or 0),
                )
                count += 1

            conn.commit()
            conn.close()
            shutil.copy2(tmp_path, str(db_file))
        finally:
            os.unlink(tmp_path)
        return count

    def import_history(self, items: List[HistoryEntry]) -> int:
        db_file = self.profile_path / "places.sqlite"
        if not db_file.exists():
            return 0

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            shutil.copy2(str(db_file), tmp_path)
            conn = sqlite3.connect(tmp_path)
            count = 0
            for entry in items:
                try:
                    existing = conn.execute("SELECT id FROM moz_places WHERE url = ?", (entry.url,)).fetchone()
                    if existing:
                        conn.execute(
                            "UPDATE moz_places SET visit_count = visit_count + ? WHERE id = ?",
                            (entry.visit_count, existing[0]),
                        )
                        place_id = existing[0]
                    else:
                        conn.execute(
                            "INSERT INTO moz_places (url, title, visit_count) VALUES (?, ?, ?)",
                            (entry.url, entry.title, entry.visit_count),
                        )
                        place_id = conn.lastrowid
                    conn.execute(
                        "INSERT OR IGNORE INTO moz_historyvisits (place_id, visit_date, visit_type) VALUES (?, ?, 1)",
                        (place_id, entry.last_visited or 0),
                    )
                    count += 1
                except sqlite3.Error:
                    pass
            conn.commit()
            conn.close()
            shutil.copy2(tmp_path, str(db_file))
        finally:
            os.unlink(tmp_path)
        return count

    def import_passwords(self, items: List[SavedPassword]) -> int:
        # Write importable CSV for use with Firefox's built-in import
        csv_path = self.profile_path / "webflow_passwords_import.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("url,username,password,httpRealm,formActionOrigin,guid,timeCreated,timeLastUsed,timePasswordChanged\n")
            for p in items:
                def esc(s: str) -> str:
                    return '"' + s.replace('"', '""') + '"'
                f.write(f"{esc(p.origin_url)},{esc(p.username)},{esc(p.password)},,,,,, \n")
        return len(items)

    def import_extensions(self, items: List[Extension]) -> int:
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
<table><tr><th>Name</th><th>Install</th><th>Version</th></tr>{rows}</table>
</body></html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return len(items)

    def import_settings(self, settings_data: dict) -> int:
        prefs_file = self.profile_path / "prefs.js"
        if not prefs_file.exists():
            return 0
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return 0
        count = 0
        mapping = {
            "homepage": "browser.startup.homepage",
            "default_search_provider": "browser.search.defaultenginename",
        }
        for src_key, ff_key in mapping.items():
            if src_key in settings_data and settings_data[src_key]:
                line = f'user_pref("{ff_key}", "{settings_data[src_key]}");\n'
                if ff_key not in content:
                    content += line
                    count += 1
        with open(prefs_file, "w", encoding="utf-8") as f:
            f.write(content)
        return count
