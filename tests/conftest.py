import logging
import random
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.celery.app import celery
from app.core import cache
from app.db.base_model import BaseModel
from app.db.session import get_unit_of_work
from app.db.unit_of_work import UnitOfWork
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

    async def expire(self, key: str, seconds: int, nx: bool = False) -> bool:
        if key not in self.data or (nx and key in self.expiry):
            return False
        self.expiry[key] = seconds
        return True

    async def ttl(self, key: str) -> int:
        if key not in self.data:
            return -2
        return self.expiry.get(key, -1)

    def pipeline(self, transaction: bool = True) -> "FakePipeline":
        return FakePipeline(self)


class FakePipeline:
    """Queues commands like redis-py's pipeline and runs them in order on execute()."""

    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self.commands: list[tuple[str, tuple, dict]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    def __getattr__(self, name: str):
        def queue(*args, **kwargs) -> "FakePipeline":
            self.commands.append((name, args, kwargs))
            return self

        return queue

    async def execute(self) -> list:
        return [
            await getattr(self.redis, name)(*args, **kwargs) for name, args, kwargs in self.commands
        ]


class SentTask:
    def __init__(self, name: str, args: tuple, eta) -> None:
        self.name = name
        self.short_name = name.rsplit(".", 1)[-1]
        self.args = args
        self.eta = eta


@pytest.fixture(autouse=True)
def sent_tasks(monkeypatch) -> list[SentTask]:
    """Records Celery tasks instead of sending them to a broker."""
    sent: list[SentTask] = []

    def send_task(name: str, args=(), eta=None, **options) -> None:
        sent.append(SentTask(name, tuple(args), eta))

    monkeypatch.setattr(celery, "send_task", send_task)
    return sent


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(cache, "redis", redis)
    return redis


async def override_get_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    async with UnitOfWork(async_session_maker) as uow:
        yield uow


app.dependency_overrides[get_unit_of_work] = override_get_unit_of_work


@pytest.fixture(autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture
async def uow() -> AsyncGenerator[UnitOfWork, None]:
    """A unit of work that commits only when the test calls uow.commit()."""
    async with UnitOfWork(async_session_maker) as uow:
        yield uow
        await uow.rollback()


@pytest.fixture
def session(uow: UnitOfWork) -> AsyncSession:
    return uow.session


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
