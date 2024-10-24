import pytest
from app.repositories.user_repository import UserRepository
from app.schemas.user import User, UserUpdate
from tests.conftest import async_session_maker


@pytest.mark.asyncio
async def test_create_user():
    async with async_session_maker() as session:
        repository = UserRepository(session)

        user_data = User(
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )

        created_user = await repository.create_user(user=user_data)

    assert created_user.username == user_data.username
    assert created_user.email == user_data.email
    assert created_user.id is not None


@pytest.mark.asyncio
async def test_get_users(test_users):
    async with async_session_maker() as session:
        repository = UserRepository(session)
        users = await repository.get_users()

    assert isinstance(users, list)
    assert len(users) == len(test_users)

    for ind, user in enumerate(users):
        assert user in test_users


@pytest.mark.asyncio
async def test_get_user_by_id(test_user):
    async with async_session_maker() as session:
        repository = UserRepository(session)
        user = await repository.get_user_by_id(test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_username(test_user):
    async with async_session_maker() as session:
        repository = UserRepository(session)
        user = await repository.get_user_by_username(test_user.username)

    assert user is not None
    assert user.username == test_user.username
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_update_user_by_id(test_user):
    async with async_session_maker() as session:
        repository = UserRepository(session)

        update_data = UserUpdate(
            post_auto_reply=True,
            reply_after=15
        )

        updated_user = await repository.update_user_by_id(
            user_id=test_user.id,
            user=update_data
        )

    assert updated_user is not None
    assert updated_user.id == test_user.id
    assert updated_user.post_auto_reply == update_data.post_auto_reply
    assert updated_user.reply_after == update_data.reply_after
