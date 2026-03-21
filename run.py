"""WebFlow entry point — starts the server and opens the browser."""
import uvicorn
import webbrowser
import threading
import time


def _open_browser() -> None:
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
