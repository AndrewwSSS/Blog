import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRegister, UserUpdate, UserInDB
from tests.fixtures import (
    session,
    test_users,
    test_user
)


@pytest.mark.asyncio
async def test_create_user(
    session: AsyncSession,
):
    repository = UserRepository(session)

    user_data = UserRegister(
        username="testuser",
        email="testuser@example.com",
        password="password123"
    )

    created_user = await repository.create(user=user_data)

    assert created_user.username == user_data.username
    assert created_user.email == user_data.email
    assert created_user.hashed_password != user_data.password
    assert created_user.id is not None


@pytest.mark.asyncio
async def test_get_all(
    test_users: [UserInDB],
    session: AsyncSession,
):
    repository = UserRepository(session)
    users = await repository.get_list()

    assert isinstance(users, list)
    assert len(users) == len(test_users)

    for ind, user in enumerate(users):
        assert user in test_users


@pytest.mark.asyncio
async def test_get_by_id(
    test_user: UserInDB,
    session: AsyncSession,
):
    repository = UserRepository(session)
    user = await repository.get_by_id(test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.username == test_user.username
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_by_username(
    test_user: UserInDB,
    session: AsyncSession,
):
    repository = UserRepository(session)
    user = await repository.get_by_username(test_user.username)

    assert user is not None
    assert user.username == test_user.username
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_update_by_id(
    test_user: UserInDB,
    session: AsyncSession,
):
    repository = UserRepository(session)

    update_data = UserUpdate(
        post_auto_reply=True,
        reply_after=15
    )

    updated_user = await repository.update_by_id(
        user_id=test_user.id,
        fields=update_data.model_dump()
    )

    assert updated_user is not None
    assert updated_user.id == test_user.id
    assert updated_user.post_auto_reply == update_data.post_auto_reply
    assert updated_user.reply_after == update_data.reply_after
