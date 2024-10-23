import asyncio
import uuid
import random
from typing import AsyncGenerator
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.validation.base_content_validator import BaseContentValidator
from app.db.session import get_session as get_async_session
from app.db.base_model import BaseModel
from app.main import app
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import Comment
from app.schemas.comment import CommentRead
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import User
from app.schemas.user import UserRead

DATABASE_URL_TEST = settings.test_database_url

engine_test = create_async_engine(DATABASE_URL_TEST, poolclass=NullPool)
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


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(scope="function", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


# @pytest.fixture(scope="session")
# def event_loop():
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#     yield loop
#     loop.close()


client = TestClient(app)


@pytest.fixture(scope="session")
async def ac() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_user() -> UserRead:
    return await create_user()


@pytest.fixture(scope="function")
async def test_post(test_user) -> PostRead:
    return await create_post(
        test_user.id
    )


@pytest.fixture(scope="function")
async def test_comment(test_post) -> CommentRead:
    return await create_comment(
        test_post.owner_id,
        test_post.id,
    )


@pytest.fixture(scope="function")
async def test_posts(test_user) -> [PostRead]:
    count = random.randint(3, 10)
    return [await create_post(test_user.id) for _ in range(count)]


@pytest.fixture(scope="function")
async def test_comments(test_post, test_user) -> [PostRead]:
    count = random.randint(3, 10)
    return [await create_comment(test_user.id, test_post.id) for _ in range(count)]


@pytest.fixture(scope="function")
async def test_users() -> [PostRead]:
    count = random.randint(3, 10)
    return [await create_user() for _ in range(count)]


async def create_comment(
    owner_id: int,
    post_id: int,
    content: str = "",
) -> CommentRead:
    async with async_session_maker() as session:
        repository = CommentRepository(session)
        comment = Comment(content=f"{content}-{uuid.uuid4()}", post_id=post_id)
        created_comment = await repository.create_comment(
            comment, owner_id, MockContentValidator
        )
        return created_comment


async def create_post(
    owner_id: int,
    content: str = "",
    title: str = ""
) -> PostRead:
    async with async_session_maker() as session:
        repository = PostRepository(session)
        post = Post(content=f"{content}-{uuid.uuid4()}", title=f"{title}-{uuid.uuid4()}")
        created_post = await repository.create_post(
            post, owner_id, MockContentValidator
        )
        return created_post


async def create_user(
    username: str = "",
    email: str = "",
    password: str = ""
) -> UserRead:
    async with async_session_maker() as session:
        repository = UserRepository(session)
        user = User(
            username=f"{username}{uuid.uuid4()}",
            password=f"{password}{uuid.uuid4()}",
            email=f"{email}{uuid.uuid4()}@gmail.com",
        )
        created_user = await repository.create_user(user)
    return created_user
