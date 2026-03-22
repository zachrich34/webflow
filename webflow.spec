# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for WebFlow.
# Produces a single self-contained WebFlow.exe (Windows) / WebFlow (Linux/macOS).
#
# Build locally:
#   pip install pyinstaller
#   pyinstaller webflow.spec
# Output: dist/WebFlow.exe

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("static", "static"),           # CSS + JS assets + icon
        ("templates", "templates"),     # Jinja2 HTML templates
    ],
    hiddenimports=[
        # --- app package (loaded dynamically by uvicorn via string "app.main:app") ---
        "app",
        "app.main",
        "app.config",
        "app.database",
        "app.models",
        "app.schemas",
        "app.security",
        "app.session_store",
        "app.routers",
        "app.routers.auth",
        "app.routers.browsers",
        "app.routers.transfer",
        "app.browsers",
        "app.browsers.base",
        "app.browsers.chrome",
        "app.browsers.firefox",
        "app.browsers.opera_gx",
        # --- uvicorn internals (not auto-detected) ---
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # --- SQLAlchemy / aiosqlite ---
        "aiosqlite",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.ext.asyncio",
        # --- cryptography / auth ---
        "passlib.handlers.bcrypt",
        "jose",
        "jose.jwt",
        # --- pywebview (native desktop window) ---
        "webview",
        "webview.platforms",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="WebFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    icon="static/icon.ico",  # App icon (taskbar + exe)
    console=False,           # No black terminal window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
