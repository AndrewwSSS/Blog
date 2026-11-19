from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import OutboxEventDB
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserInDB
from app.services.user_service import VERIFICATION_RESEND_COOLDOWN_SECONDS
from tests.conftest import FakeRedis
from tests.fixtures import async_session_maker

RESEND_URL = "/api/v1/users/verification/resend"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def all_events() -> list[OutboxEventDB]:
    async with async_session_maker() as session:
        result = await session.execute(select(OutboxEventDB).order_by(OutboxEventDB.id))
        return list(result.scalars().all())


async def test_unverified_user_gets_event_and_cooldown(
    client: AsyncClient, test_user: UserInDB, fake_redis: FakeRedis
):
    response = await client.post(RESEND_URL, json={"email": test_user.email})

    assert response.status_code == 202
    [event] = await all_events()
    assert (event.topic, event.payload) == ("new-user-registration", {"id": test_user.id})
    assert event.published_at is None
    key = f"verification-resend:{test_user.email.lower()}"
    assert fake_redis.expiry[key] == VERIFICATION_RESEND_COOLDOWN_SECONDS


async def test_second_request_within_cooldown_is_ignored(client: AsyncClient, test_user: UserInDB):
    first = await client.post(RESEND_URL, json={"email": test_user.email})
    second = await client.post(RESEND_URL, json={"email": test_user.email.upper()})

    assert (first.status_code, second.status_code) == (202, 202)
    assert first.json() == second.json()
    assert len(await all_events()) == 1


async def test_unknown_and_active_addresses_look_the_same(
    client: AsyncClient, test_user: UserInDB, test_users: list[UserInDB], session: AsyncSession
):
    active = test_users[0]
    await UserRepository(session).update_by_id(active.id, is_active=True)

    known = await client.post(RESEND_URL, json={"email": test_user.email})
    unknown = await client.post(RESEND_URL, json={"email": "nobody@example.com"})
    already_active = await client.post(RESEND_URL, json={"email": active.email})

    for response in (unknown, already_active):
        assert response.status_code == known.status_code == 202
        assert response.json() == known.json()
    [event] = await all_events()
    assert event.payload == {"id": test_user.id}


async def test_redis_down_sends_nothing(
    client: AsyncClient, test_user: UserInDB, fake_redis: FakeRedis, monkeypatch
):
    async def failing_set(*args, **kwargs):
        raise RedisConnectionError("redis down")

    monkeypatch.setattr(fake_redis, "set", failing_set)

    response = await client.post(RESEND_URL, json={"email": test_user.email})

    assert response.status_code == 202
    assert await all_events() == []


async def test_invalid_email_is_422(client: AsyncClient):
    response = await client.post(RESEND_URL, json={"email": "not-an-email"})

    assert response.status_code == 422
