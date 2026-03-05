"""
Database setup and session management.
Supports PostgreSQL (Supabase) and SQLite (local dev).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import DATABASE_URL

# Engine args differ by driver
_is_sqlite = DATABASE_URL.startswith("sqlite")
_engine_kwargs = {"echo": False}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        from .models import Document, ExtractedEntity, User, AuditLog  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency: yield an async DB session."""
    async with async_session() as session:
        yield session
