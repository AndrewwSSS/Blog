import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_email_verification_token
from app.main import app
from app.models import OutboxEventDB
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.pubsub.outbox import delete_old_published_events, relay_pending_events
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserInDB, UserRegister
from app.services.user_service import UserService
from tests.fixtures import async_session_maker


async def all_events() -> list[OutboxEventDB]:
    async with async_session_maker() as session:
        result = await session.execute(select(OutboxEventDB).order_by(OutboxEventDB.id))
        return list(result.scalars().all())


async def add_events(*payloads: dict, published_at: datetime | None = None) -> None:
    async with async_session_maker() as session:
        for payload in payloads:
            session.add(OutboxEventDB(topic="t", payload=payload, published_at=published_at))
        await session.commit()


@pytest.fixture
def kafka_down(monkeypatch) -> None:
    async def failing_publish(topic: str, data: str, key: str | None = None) -> None:
        raise AsyncKafkaProducer.ProducerNotInitialized()

    monkeypatch.setattr(AsyncKafkaProducer, "publish", failing_publish)


@pytest.fixture
def kafka_up(monkeypatch) -> list[tuple[str, dict]]:
    published = []

    async def fake_publish(topic: str, data: str, key: str | None = None) -> None:
        published.append((topic, json.loads(data)))

    monkeypatch.setattr(AsyncKafkaProducer, "publish", fake_publish)
    return published


def user_service(session: AsyncSession) -> UserService:
    return UserService(UserRepository(session), OutboxRepository(session))


def registration(username: str = "alice") -> UserRegister:
    return UserRegister(username=username, email=f"{username}@example.com", password="pw")


async def test_registration_with_kafka_down_keeps_event_in_outbox(session, kafka_down):
    user = await user_service(session).create(registration())

    [event] = await all_events()
    assert (event.topic, event.payload) == ("new-user-registration", {"id": user.id})
    assert event.published_at is None


async def test_registration_with_kafka_up_publishes_immediately(session, kafka_up):
    user = await user_service(session).create(registration())

    assert kafka_up == [("new-user-registration", {"id": user.id})]
    [event] = await all_events()
    assert event.published_at is not None


async def test_failed_registration_writes_no_event(session, kafka_up):
    service = user_service(session)
    await service.create(registration("alice"))

    with pytest.raises(HTTPException) as exc_info:
        await service.create(registration("alice"))

    assert exc_info.value.status_code == 400
    assert len(await all_events()) == 1


async def test_register_endpoint_returns_201_when_kafka_is_down(kafka_down):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/register",
            json={"username": "bob", "email": "bob@example.com", "password": "pw"},
        )

    assert response.status_code == 201
    [event] = await all_events()
    assert event.payload == {"id": response.json()["id"]}


async def test_verification_writes_new_active_user_event(session, test_user: UserInDB, kafka_down):
    await user_service(session).verify_user(generate_email_verification_token(test_user.email))

    [event] = await all_events()
    assert (event.topic, event.payload) == ("new-active-user", {"email": test_user.email})


class FakeProducer:
    def __init__(self, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.sent: list[dict] = []
        self.stopped = False

    async def start(self) -> None:
        if self.fail_start:
            raise ConnectionError("kafka down")

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(self, topic: str, value: bytes) -> None:
        payload = json.loads(value)
        if payload.get("fail"):
            raise RuntimeError("message rejected")
        self.sent.append(payload)


async def test_relay_publishes_pending_events_in_order_once(session):
    await add_events({"n": 1}, {"n": 2}, {"n": 3})
    producer = FakeProducer()

    published = await relay_pending_events(OutboxRepository(session), lambda: producer)
    again = await relay_pending_events(OutboxRepository(session), lambda: FakeProducer())

    assert (published, again) == (3, 0)
    assert producer.sent == [{"n": 1}, {"n": 2}, {"n": 3}]
    assert all(event.published_at for event in await all_events())


async def test_relay_leaves_events_pending_when_kafka_is_down(session):
    await add_events({"n": 1})
    producer = FakeProducer(fail_start=True)

    published = await relay_pending_events(OutboxRepository(session), lambda: producer)

    [event] = await all_events()
    assert published == 0
    assert (event.published_at, event.attempts) == (None, 0)
    assert producer.stopped


async def test_relay_records_failure_and_continues(session):
    await add_events({"n": 1}, {"fail": True}, {"n": 3})
    producer = FakeProducer()

    published = await relay_pending_events(OutboxRepository(session), lambda: producer)

    first, failed, third = await all_events()
    assert published == 2
    assert producer.sent == [{"n": 1}, {"n": 3}]
    assert first.published_at and third.published_at
    assert failed.published_at is None
    assert failed.attempts == 1
    assert "message rejected" in failed.last_error


async def test_cleanup_deletes_only_old_published_events(session):
    now = datetime.now(UTC)
    await add_events({"age": "old"}, published_at=now - timedelta(days=8))
    await add_events({"age": "recent"}, published_at=now - timedelta(days=1))
    await add_events({"age": "pending"})

    deleted = await delete_old_published_events(OutboxRepository(session))

    assert deleted == 1
    assert [event.payload["age"] for event in await all_events()] == ["recent", "pending"]
