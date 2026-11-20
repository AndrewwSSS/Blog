import logging

import pytest

from app.db.unit_of_work import UnitOfWork
from app.models import UserDB
from app.repositories.user_repository import UserRepository
from tests.fixtures import async_session_maker


async def create_user(uow: UnitOfWork, username: str = "alice") -> int:
    user = UserDB(username=username, hashed_password="hash", email=f"{username}@example.com")
    uow.session.add(user)
    await uow.session.flush()
    return user.id


async def user_exists(user_id: int) -> bool:
    async with async_session_maker() as other:
        return await UserRepository(other).get_by_id(user_id) is not None


async def test_block_commits_on_success():
    async with UnitOfWork(async_session_maker) as uow:
        user_id = await create_user(uow)
        assert not await user_exists(user_id)

    assert await user_exists(user_id)


async def test_block_rolls_back_on_error_and_skips_callbacks():
    calls = []

    with pytest.raises(RuntimeError):
        async with UnitOfWork(async_session_maker) as uow:
            user_id = await create_user(uow)
            uow.after_commit(calls.append, "ran")
            raise RuntimeError("boom")

    assert not await user_exists(user_id)
    assert calls == []


async def test_callbacks_run_after_commit_in_order():
    calls = []

    async def async_callback(name: str) -> None:
        calls.append((name, await user_exists(user_id)))

    async with UnitOfWork(async_session_maker) as uow:
        user_id = await create_user(uow)
        uow.after_commit(async_callback, "async")
        uow.after_commit(lambda name, flag: calls.append((name, flag)), "sync", flag=True)
        assert calls == []

    assert calls == [("async", True), ("sync", True)]


async def test_callbacks_run_once():
    calls = []

    async with UnitOfWork(async_session_maker) as uow:
        uow.after_commit(calls.append, 1)
        await uow.commit()
        await uow.commit()

    assert calls == [1]


async def test_failing_callback_is_logged_and_others_still_run(caplog):
    calls = []

    def failing() -> None:
        raise RuntimeError("broker down")

    with caplog.at_level(logging.ERROR, logger="app.db.unit_of_work"):
        async with UnitOfWork(async_session_maker) as uow:
            user_id = await create_user(uow)
            uow.after_commit(failing)
            uow.after_commit(calls.append, "next")

    assert await user_exists(user_id)
    assert calls == ["next"]
    assert "After-commit callback" in caplog.text
