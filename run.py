"""WebFlow entry point — starts the FastAPI server and opens a native desktop window."""
import os
import sys
import threading
import time

import urllib.request
import urllib.error

import uvicorn
import webview


def resource_path(relative: str) -> str:
    """Resolve a path that works both in dev mode and in a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def _start_server() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="warning",
    )


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Poll until the server responds or timeout is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


if __name__ == "__main__":
    # Start FastAPI in a daemon thread — it dies when the window is closed
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Wait until uvicorn is actually ready (up to 15 s)
    if not _wait_for_server("http://127.0.0.1:8765/api/health"):
        import tkinter, tkinter.messagebox
        root = tkinter.Tk(); root.withdraw()
        tkinter.messagebox.showerror("WebFlow", "Le serveur n'a pas pu démarrer.\nEssaie de relancer l'application.")
        sys.exit(1)

    # Open the app as a native desktop window (not a browser tab)
    webview.create_window(
        "WebFlow",
        "http://127.0.0.1:8765",
        width=1280,
        height=800,
        resizable=True,
        min_size=(900, 600),
    )
    webview.start()  # blocks until the window is closed
