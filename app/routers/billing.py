"""Billing endpoints — Stripe subscriptions (freemium + pro + premium)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import CheckoutResponse, SubscriptionStatusResponse

def _parse_early_adopter_cutoff() -> Optional[datetime]:
    """Parse WEBFLOW_EARLY_ADOPTER_CUTOFF from config (ISO date string like '2025-06-01')."""
    raw = settings.early_adopter_cutoff.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

EARLY_ADOPTER_CUTOFF: Optional[datetime] = _parse_early_adopter_cutoff()

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Tier constants — single source of truth for feature gating
# ---------------------------------------------------------------------------

FREE_DATA_TYPES = {"bookmarks", "history"}
PRO_DATA_TYPES  = {"bookmarks", "history", "passwords", "extensions", "settings"}
PREMIUM_DATA_TYPES = PRO_DATA_TYPES  # same data types + sync + early_access flags

TIER_FEATURES: dict[str, list[str]] = {
    "free":    ["bookmarks", "history"],
    "beta":    ["bookmarks", "history", "passwords", "extensions", "settings"],
    "pro":     ["bookmarks", "history", "passwords", "extensions", "settings"],
    "premium": ["bookmarks", "history", "passwords", "extensions", "settings",
                "daily_sync", "early_access"],
}

PLAN_PRICES: dict[str, str] = {
    "pro":     settings.stripe_pro_price_id,
    "premium": settings.stripe_premium_price_id,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_stripe():
    """Return the configured stripe module or raise 503."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured — set STRIPE_SECRET_KEY")
    import stripe as stripe_lib
    stripe_lib.api_key = settings.stripe_secret_key
    return stripe_lib


def get_effective_tier(user: User) -> str:
    """Return the user's active tier.

    Priority order:
    1. Beta mode → everyone is 'beta' (all features free)
    2. Early adopter (registered before cutoff) → lifetime 'premium'
    3. Active paid subscription → 'pro' or 'premium'
    4. Default → 'free'
    """
    if settings.beta_mode:
        return "beta"

    # Early adopter: lifetime premium for users who joined before the cutoff
    if EARLY_ADOPTER_CUTOFF and user.created_at:
        created = user.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < EARLY_ADOPTER_CUTOFF:
            return "premium"

    if user.subscription_tier in ("pro", "premium"):
        if user.subscription_expires is None:
            return user.subscription_tier
        expires = user.subscription_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > datetime.now(timezone.utc):
            return user.subscription_tier

    return "free"


def get_allowed_data_types(tier: str) -> set[str]:
    if tier in ("pro", "premium", "beta"):
        return PRO_DATA_TYPES
    return FREE_DATA_TYPES


# ---------------------------------------------------------------------------
# GET /api/billing/status
# ---------------------------------------------------------------------------

@router.get("/status", response_model=SubscriptionStatusResponse)
async def billing_status(user_jti: tuple = Depends(get_current_user)):
    user, _ = user_jti
    tier = get_effective_tier(user)
    return SubscriptionStatusResponse(
        tier=tier,
        expires=user.subscription_expires,
        features=TIER_FEATURES.get(tier, TIER_FEATURES["free"]),
        is_active=tier != "free",
    )


# ---------------------------------------------------------------------------
# POST /api/billing/checkout/{plan}
# ---------------------------------------------------------------------------

@router.post("/checkout/{plan}", response_model=CheckoutResponse)
async def create_checkout(
    plan: str,
    user_jti: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail=f"Unknown plan '{plan}'. Use 'pro' or 'premium'.")

    price_id = PLAN_PRICES[plan]
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Price ID for '{plan}' not configured — set STRIPE_{plan.upper()}_PRICE_ID")

    stripe = _get_stripe()
    user, _ = user_jti

    # Create or reuse Stripe customer
    if user.stripe_customer_id:
        customer_id = user.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id), "username": user.username},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=(
            f"{settings.app_base_url}/billing/success"
            "?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{settings.app_base_url}/billing/cancel",
        client_reference_id=str(user.id),
        metadata={"plan": plan},
    )

    return CheckoutResponse(url=session.url)


# ---------------------------------------------------------------------------
# POST /api/billing/portal  (manage existing subscription)
# ---------------------------------------------------------------------------

@router.post("/portal", response_model=CheckoutResponse)
async def billing_portal(user_jti: tuple = Depends(get_current_user)):
    stripe = _get_stripe()
    user, _ = user_jti

    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found — subscribe first")

    portal = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.app_base_url}/",
    )
    return CheckoutResponse(url=portal.url)


# ---------------------------------------------------------------------------
# POST /api/billing/webhook  (Stripe → server, for renewals / cancellations)
# ---------------------------------------------------------------------------

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    stripe = _get_stripe()

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    etype = event["type"]
    if etype in ("customer.subscription.created", "customer.subscription.updated"):
        await _handle_subscription_updated(event["data"]["object"])
    elif etype == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"])

    return {"status": "ok"}


async def _handle_subscription_updated(sub: dict) -> None:
    customer_id: Optional[str] = sub.get("customer")
    if not customer_id:
        return

    items = sub.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else ""

    if price_id == settings.stripe_premium_price_id:
        tier = "premium"
    elif price_id == settings.stripe_pro_price_id:
        tier = "pro"
    else:
        tier = "free"

    expires_ts = sub.get("current_period_end")
    expires_dt = datetime.fromtimestamp(expires_ts, tz=timezone.utc) if expires_ts else None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user and sub.get("status") == "active":
            user.subscription_tier = tier
            user.subscription_expires = expires_dt
            user.stripe_subscription_id = sub.get("id")
            await db.commit()


async def _handle_subscription_deleted(sub: dict) -> None:
    customer_id: Optional[str] = sub.get("customer")
    if not customer_id:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_tier = "free"
            user.subscription_expires = None
            user.stripe_subscription_id = None
            await db.commit()
