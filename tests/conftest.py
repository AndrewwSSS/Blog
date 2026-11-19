import logging
import random
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core import cache
from app.db.base_model import BaseModel
from app.db.session import get_session as get_async_session
from app.schemas.comment import CommentInDB
from app.schemas.post import PostInDB
from app.schemas.user import UserInDB
from tests.fixtures import (
    async_session_maker,
    create_comment,
    create_post,
    create_user,
    engine_test,
)

logging.disable(logging.INFO)

REQUIRED_ENV = {
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "password",
    "POSTGRES_DB": "blog",
    "POSTGRES_HOST": "db",
    "SECRET_KEY": "secret",
    "EMAIL_TOKEN_SALT": "salt",
    "KAFKA_URL": "kafka:9092",
    "SMTP_USER": "smtp-user",
    "SMTP_USER_PASSWORD": "smtp-password",
}


@pytest.fixture
def required_env(monkeypatch) -> None:
    """Set every required setting, so Settings() can be built without a .env file."""
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}
        self.expiry: dict[str, int] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(
        self, key: str, value: str | bytes, ex: int | None = None, nx: bool = False
    ) -> bool | None:
        if nx and key in self.data:
            return None
        self.data[key] = value.encode() if isinstance(value, str) else value
        if ex is not None:
            self.expiry[key] = ex
        return True

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


@pytest.fixture(autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_user() -> UserInDB:
    return await create_user()


@pytest.fixture
async def test_users() -> list[UserInDB]:
    return [await create_user() for _ in range(random.randint(3, 5))]


@pytest.fixture
async def test_post(test_user) -> PostInDB:
    return await create_post(test_user.id)


@pytest.fixture
async def test_posts(test_user) -> list[PostInDB]:
    return [await create_post(test_user.id) for _ in range(random.randint(3, 5))]


@pytest.fixture
async def test_comment(test_post) -> CommentInDB:
    return await create_comment(test_post.owner_id, test_post.id)


@pytest.fixture
async def test_comments(test_post, test_user) -> list[CommentInDB]:
    return [await create_comment(test_user.id, test_post.id) for _ in range(random.randint(3, 5))]
