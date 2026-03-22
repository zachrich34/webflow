"""SQLAlchemy async engine and session factory."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create all tables on startup and apply any pending column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _run_migrations(conn)


async def _run_migrations(conn) -> None:
    """Safely add new columns to existing tables (SQLite ALTER TABLE)."""
    migrations = [
        ("users", "subscription_tier",     "VARCHAR(16) NOT NULL DEFAULT 'free'"),
        ("users", "subscription_expires",  "DATETIME"),
        ("users", "stripe_customer_id",    "VARCHAR(64)"),
        ("users", "stripe_subscription_id","VARCHAR(64)"),
    ]
    for table, column, definition in migrations:
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        except Exception:
            pass  # Column already exists — safe to ignore


async def get_db():
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
