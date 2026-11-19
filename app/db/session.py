from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url


def make_engine(url: str, **kwargs) -> AsyncEngine:
    """Create an async engine; tests use it too, so they get the same connection settings."""
    if make_url(url).drivername == "postgresql+asyncpg":
        # Keeps SQL date() and casts of timestamptz columns in UTC, whatever the server default is.
        kwargs.setdefault("connect_args", {"server_settings": {"timezone": "UTC"}})
    return create_async_engine(url, **kwargs)


engine = make_engine(SQLALCHEMY_DATABASE_URL)


def make_sessionmaker(bind: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the session factory; tests use it too, so they run with production settings."""
    return async_sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


async_session = make_sessionmaker(engine)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
