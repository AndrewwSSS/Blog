from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"server_settings": {"timezone": "UTC"}},
)


def make_sessionmaker(bind: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the session factory; tests use it too, so they run with production settings."""
    return async_sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


async_session = make_sessionmaker(engine)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
