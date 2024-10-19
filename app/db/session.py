from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
async_session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
