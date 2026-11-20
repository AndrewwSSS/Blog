import logging
from pathlib import Path
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_unit_of_work
from app.db.unit_of_work import UnitOfWork
from app.models import UserDB
from app.main import app
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
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


class FailingCommitUnitOfWork(UnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("commit failed")


async def failing_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    async with FailingCommitUnitOfWork(async_session_maker) as uow:
        yield uow


async def test_failed_commit_returns_500_and_publishes_nothing(monkeypatch):
    """Guards the FastAPI behaviour this design relies on: the request's commit
    runs before the response is sent, so a failed commit is never reported as 201."""
    published = []

    async def fake_publish(topic: str, data: str, key: str | None = None) -> None:
        published.append(topic)

    monkeypatch.setattr(AsyncKafkaProducer, "publish", fake_publish)
    monkeypatch.setitem(app.dependency_overrides, get_unit_of_work, failing_unit_of_work)
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/register",
            json={"username": "dave", "email": "dave@example.com", "password": "pw"},
        )

    assert response.status_code == 500
    assert published == []
    async with async_session_maker() as other:
        assert await UserRepository(other).get_by_username("dave") is None


def test_app_code_opens_sessions_only_through_a_unit_of_work():
    app_dir = Path(__file__).parent.parent / "app"
    offenders = [
        str(path.relative_to(app_dir))
        for path in app_dir.rglob("*.py")
        if "async_session()" in path.read_text()
    ]

    assert offenders == []
