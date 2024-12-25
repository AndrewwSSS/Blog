import random
import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import CommentInDB, CommentCreate
from app.schemas.post import Post, PostInDB, PostRead
from app.schemas.user import UserRegister, UserInDB
from tests.conftest import async_session_maker, app


@pytest.fixture(scope="session")
async def ac() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
async def test_user() -> UserInDB:
    return await create_user()


@pytest.fixture(scope="function")
async def test_post(test_user) -> PostInDB:
    return await create_post(
        test_user.id
    )


@pytest.fixture(scope="function")
async def test_comment(test_post) -> CommentInDB:
    return await create_comment(
        test_post.owner_id,
        test_post.id,
    )


@pytest.fixture(scope="function")
async def test_posts(test_user) -> [PostRead]:
    count = random.randint(3, 5)
    return [await create_post(test_user.id) for _ in range(count)]


@pytest.fixture(scope="function")
async def test_comments(test_post, test_user) -> [PostRead]:
    count = random.randint(3, 5)
    return [await create_comment(test_user.id, test_post.id) for _ in range(count)]


@pytest.fixture(scope="function")
async def test_users() -> [PostRead]:
    count = random.randint(3, 5)
    return [await create_user() for _ in range(count)]


async def create_comment(
    owner_id: int,
    post_id: int,
    content: str = "",
) -> CommentInDB:
    async with async_session_maker() as session:
        repository = CommentRepository(session)
        comment = CommentCreate(content=f"{content}-{uuid.uuid4()}", post_id=post_id)
        created_comment = await repository.create(
            **comment.model_dump(),
            owner_id=owner_id
        )
    return created_comment


async def create_post(
    owner_id: int,
    content: str = "",
    title: str = ""
) -> PostInDB:
    async with async_session_maker() as session:
        repository = PostRepository(session)
        post = Post(content=f"{content}-{uuid.uuid4()}", title=f"{title}-{uuid.uuid4()}")
        created_post = await repository.create(
            **post.model_dump(),
            owner_id=owner_id
        )
    return created_post


async def create_user(
    username: str = "",
    email: str = "",
    password: str = ""
) -> UserInDB:
    async with async_session_maker() as session:
        repository = UserRepository(session)

        created_user = await repository.create(
            username=f"{username}{uuid.uuid4()}",
            hashed_password=f"{password}{uuid.uuid4()}",
            email=f"{email}{uuid.uuid4()}@gmail.com",
        )
    return created_user
