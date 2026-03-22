"""Abstract base classes for browser data extraction and import."""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Bookmark:
    title: str
    url: str
    folder: str = ""
    added: Optional[int] = None  # Unix timestamp (ms)


@dataclass
class HistoryEntry:
    url: str
    title: str
    visit_count: int
    last_visited: Optional[int] = None  # Unix timestamp (µs for Chrome, ms for Firefox)


@dataclass
class SavedPassword:
    origin_url: str
    username: str
    password: str  # decrypted plaintext — handled only in memory, never logged


@dataclass
class Extension:
    name: str
    ext_id: str
    version: str
    store_url: str = ""  # link to reinstall


@dataclass
class BrowserData:
    bookmarks: List[Bookmark] = field(default_factory=list)
    history: List[HistoryEntry] = field(default_factory=list)
    passwords: List[SavedPassword] = field(default_factory=list)
    extensions: List[Extension] = field(default_factory=list)
    settings: dict = field(default_factory=dict)


@dataclass
class ProfileInfo:
    browser: str
    profile: str
    path: str
    available: bool = True


class BrowserExtractor(ABC):
    """Reads data from a browser profile on the local machine."""

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path

    @abstractmethod
    def extract_bookmarks(self) -> List[Bookmark]:
        ...

    @abstractmethod
    def extract_history(self, days: int = 90) -> List[HistoryEntry]:
        ...

    @abstractmethod
    def extract_passwords(self) -> List[SavedPassword]:
        """
        Extracts saved passwords.
        On Chromium: uses OS keychain to decrypt the AES key stored in Local State.
        On Firefox: uses NSS / logins.json.
        Returns plaintext credentials — caller must encrypt before persisting.
        """
        ...

    @abstractmethod
    def extract_extensions(self) -> List[Extension]:
        ...

    @abstractmethod
    def extract_settings(self) -> dict:
        ...

    def extract_all(self, data_types: List[str], days: int = 90) -> BrowserData:
        data = BrowserData()
        if "bookmarks" in data_types:
            data.bookmarks = self.extract_bookmarks()
        if "history" in data_types:
            data.history = self.extract_history(days)
        if "passwords" in data_types:
            data.passwords = self.extract_passwords()
        if "extensions" in data_types:
            data.extensions = self.extract_extensions()
        if "settings" in data_types:
            data.settings = self.extract_settings()
        return data


class BrowserImporter(ABC):
    """Writes data into a browser profile on the local machine."""

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path

    @abstractmethod
    def import_bookmarks(self, items: List[Bookmark]) -> int:
        ...

    @abstractmethod
    def import_history(self, items: List[HistoryEntry]) -> int:
        ...

    @abstractmethod
    def import_passwords(self, items: List[SavedPassword]) -> int:
        ...

    @abstractmethod
    def import_extensions(self, items: List[Extension]) -> int:
        """Returns count of extensions listed (cannot auto-install)."""
        ...

    @abstractmethod
    def import_settings(self, settings: dict) -> int:
        ...

    def import_data(self, data: BrowserData, data_types: List[str]) -> dict:
        """Run all selected imports and return a count summary."""
        summary = {}
        if "bookmarks" in data_types:
            summary["bookmarks"] = self.import_bookmarks(data.bookmarks)
        if "history" in data_types:
            summary["history"] = self.import_history(data.history)
        if "passwords" in data_types:
            summary["passwords"] = self.import_passwords(data.passwords)
        if "extensions" in data_types:
            summary["extensions"] = self.import_extensions(data.extensions)
        if "settings" in data_types:
            summary["settings"] = self.import_settings(data.settings)
        return summary


def get_platform() -> str:
    """Return 'linux', 'darwin', or 'win32'."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "darwin"
    return "win32"
