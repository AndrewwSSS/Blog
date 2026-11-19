from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

# Keeps SQL date() and casts of timestamptz columns in UTC, whatever the server default is.
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"server_settings": {"timezone": "UTC"}},
)

# noinspection PyTypeChecker
async_session = sessionmaker(
    bind=engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
