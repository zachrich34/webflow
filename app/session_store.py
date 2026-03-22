"""
In-memory session key store.

Maps JWT JTI → Fernet instance.
The encryption key is NEVER written to disk or the database.
It lives only in this dict for the lifetime of the server process.
On server restart, users must log in again to re-derive their key.
"""
from cryptography.fernet import Fernet

_store: dict[str, Fernet] = {}


def set_key(jti: str, fernet: Fernet) -> None:
    """Store a Fernet instance for a session."""
    _store[jti] = fernet


def get_key(jti: str) -> Fernet | None:
    """Retrieve the Fernet instance for a session, or None if not found."""
    return _store.get(jti)


def clear_key(jti: str) -> None:
    """Remove the Fernet instance on logout or token expiry."""
    _store.pop(jti, None)


def active_sessions() -> int:
    """Return number of active in-memory sessions (for health checks)."""
    return len(_store)
