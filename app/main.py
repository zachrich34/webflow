"""FastAPI application — wires together all routers, middleware, and static files."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.database import init_db
from app.routers import auth, browsers, transfer
from app.routers import billing


# ---------------------------------------------------------------------------
# Rate limiter (slowapi wraps limits.io)
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="WebFlow",
    description="Transfer your browser data — bookmarks, history, passwords — between browsers.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — only allow localhost (local tool)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8765", "http://127.0.0.1:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(browsers.router)
app.include_router(transfer.router)
app.include_router(billing.router)


# ---------------------------------------------------------------------------
# Static files and SPA
# ---------------------------------------------------------------------------

import os
import sys
from pathlib import Path

# When bundled with PyInstaller (--onefile), files are extracted to sys._MEIPASS.
# In normal dev mode, fall back to the project root derived from __file__.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------------------------
# Stripe redirect landing pages
# ---------------------------------------------------------------------------

@app.get("/billing/success", include_in_schema=False)
async def billing_success(session_id: str = ""):
    """Verify Stripe checkout and activate subscription, then show confirmation."""
    from fastapi.responses import HTMLResponse
    from app.config import settings as cfg

    async def _activate(sid: str) -> tuple[bool, str, str]:
        if not sid or not cfg.stripe_secret_key:
            return False, "free", "Configuration error"
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = cfg.stripe_secret_key
            session = stripe_lib.checkout.Session.retrieve(sid, expand=["subscription"])
            if session.payment_status != "paid" or not session.client_reference_id:
                return False, "free", "Payment not completed"

            plan = session.metadata.get("plan", "pro")
            user_id = int(session.client_reference_id)
            sub = session.subscription

            expires_dt = None
            if sub and sub.current_period_end:
                from datetime import datetime, timezone
                expires_dt = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)

            from app.database import AsyncSessionLocal
            from app.models import User
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.subscription_tier = plan
                    user.subscription_expires = expires_dt
                    if sub:
                        user.stripe_subscription_id = sub.id
                    cust = session.customer
                    if cust:
                        user.stripe_customer_id = cust if isinstance(cust, str) else cust.id
                    await db.commit()
            return True, plan, ""
        except Exception as exc:
            return False, "free", str(exc)

    ok, plan, err = await _activate(session_id)

    if ok:
        body = f"""
        <h2>✅ Abonnement {plan.title()} activé !</h2>
        <p>Retourne dans l'application WebFlow et clique sur <strong>Actualiser l'abonnement</strong>.</p>
        <p style="color:#888;font-size:.85rem">Tu peux fermer cet onglet.</p>
        """
    else:
        body = f"""
        <h2>❌ Erreur de paiement</h2>
        <p>{err or "Paiement incomplet."}</p>
        <p>Retourne dans WebFlow et réessaie.</p>
        """

    return HTMLResponse(f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
    <title>WebFlow — Paiement</title>
    <style>body{{font-family:system-ui,sans-serif;background:#0d0d1a;color:#e8e8f0;
    display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
    .box{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
    border-radius:16px;padding:40px;max-width:480px;text-align:center}}
    h2{{margin-bottom:16px}}p{{color:rgba(255,255,255,.65);line-height:1.6}}</style>
    </head><body><div class="box">{body}</div></body></html>""")


@app.get("/billing/cancel", include_in_schema=False)
async def billing_cancel():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
    <title>WebFlow — Paiement annulé</title>
    <style>body{font-family:system-ui,sans-serif;background:#0d0d1a;color:#e8e8f0;
    display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
    .box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
    border-radius:16px;padding:40px;max-width:480px;text-align:center}
    h2{margin-bottom:16px}p{color:rgba(255,255,255,.65);line-height:1.6}</style>
    </head><body><div class="box">
    <h2>Paiement annulé</h2>
    <p>Tu peux fermer cet onglet et retourner dans WebFlow.</p>
    </div></body></html>""")


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    from app import session_store
    return {"status": "ok", "active_sessions": session_store.active_sessions()}
