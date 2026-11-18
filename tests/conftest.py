from typing import AsyncGenerator
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core import cache
from app.core.config import settings
from app.core.validation.base_content_validator import BaseContentValidator
from app.db.session import get_session as get_async_session
from app.db.base_model import BaseModel


DATABASE_URL_TEST = settings.test_database_url


logging.disable(logging.INFO)

engine_test = create_async_engine(
    DATABASE_URL_TEST,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine_test.sync_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_maker = sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False
)


class MockContentValidator(BaseContentValidator):
    async def validate_post(self, content: str, title: str) -> bool:
        return True

    async def validate_comment(self, content: str) -> bool:
        return True


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        self.data[key] = value.encode() if isinstance(value, str) else value

    async def incr(self, key: str) -> int:
        value = int(self.data.get(key, b"0")) + 1
        self.data[key] = str(value).encode()
        return value


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(cache, "redis", redis)
    return redis


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(scope="function", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


client = TestClient(app)