"""WebFlow entry point — starts the FastAPI server and opens a native desktop window."""
import os
import sys
import threading
import time

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


if __name__ == "__main__":
    # Start FastAPI in a daemon thread — it dies when the window is closed
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    # Give uvicorn a moment to bind the port before the webview opens
    time.sleep(1.2)

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
