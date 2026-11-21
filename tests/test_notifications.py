import json
from types import SimpleNamespace

import pytest
from elastic_transport import ConnectionError as ElasticConnectionError
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import verify_verification_token
from app.pubsub import async_kafka_consumer, async_kafka_producer, outbox
from app.pubsub.async_kafka_consumer import AsyncKafkaConsumer
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.pubsub.services import mail_service
from app.schemas.user import UserInDB
from app.services.post_service import PostService
from tests.fixtures import (
    async_session_maker,
    create_user,
)


def kafka_message(topic: str, payload: dict, offset: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        topic=topic,
        partition=0,
        offset=offset,
        value=json.dumps(payload).encode("utf-8"),
    )


class FakeKafkaConsumer:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeEmailService:
    sent: list[tuple[str, str]] = []
    verification_urls: list[str] = []

    def __init__(self, user: UserInDB) -> None:
        self.user = user

    async def send_verification_email(self, verification_url: str) -> bool:
        self.sent.append(("verification", self.user.email))
        self.verification_urls.append(verification_url)
        return True

    async def send_welcome_email(self) -> bool:
        self.sent.append(("welcome", self.user.email))
        return True


@pytest.fixture
def consumer(monkeypatch) -> AsyncKafkaConsumer:
    FakeEmailService.sent = []
    FakeEmailService.verification_urls = []
    monkeypatch.setattr(async_kafka_consumer, "async_session", async_session_maker)
    monkeypatch.setattr(async_kafka_consumer, "EmailService", FakeEmailService)
    consumer = AsyncKafkaConsumer.__new__(AsyncKafkaConsumer)
    consumer.consumer = FakeKafkaConsumer()
    consumer.topic_callbacks = {
        "new-user-registration": consumer._handle_new_user_registration,
        "new-active-user": consumer._handle_new_active_user,
    }
    return consumer


async def test_bad_message_does_not_stop_the_batch(
    consumer: AsyncKafkaConsumer,
    test_user: UserInDB,
):
    batch = {
        "partition-0": [
            kafka_message("new-active-user", {"email": "missing@example.com"}, 0),
            kafka_message("new-active-user", {"wrong": "payload"}, 1),
            kafka_message(
                "new-user-registration",
                {"id": test_user.id},
                2,
            ),
        ]
    }

    await consumer._process_batch(batch)

    assert FakeEmailService.sent == [("verification", test_user.email)]
    assert consumer.consumer.commits == 1


async def test_consumer_builds_verification_link(
    consumer: AsyncKafkaConsumer,
    test_user: UserInDB,
    monkeypatch,
):
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://blog.example.com/")
    message = kafka_message("new-user-registration", {"id": test_user.id})

    await consumer._process_batch({"p": [message]})

    [url] = FakeEmailService.verification_urls
    prefix = "https://blog.example.com/api/v1/users/verification/"
    assert url.startswith(prefix)
    assert verify_verification_token(url.removeprefix(prefix)) == test_user.email


async def test_empty_batch_is_not_committed(consumer: AsyncKafkaConsumer):
    await consumer._process_batch({})

    assert consumer.consumer.commits == 0


async def test_welcome_email_is_sent_once(consumer: AsyncKafkaConsumer):
    user = await create_user()
    message = kafka_message("new-active-user", {"email": user.email})

    await consumer._process_batch({"p": [message]})
    await consumer._process_batch({"p": [message]})

    assert FakeEmailService.sent == [("welcome", user.email)]


class FakeAIOKafkaProducer:
    fail_start = True
    stopped = 0

    def __init__(self, **kwargs) -> None:
        pass

    async def start(self) -> None:
        if FakeAIOKafkaProducer.fail_start:
            raise ConnectionError("kafka down")

    async def stop(self) -> None:
        FakeAIOKafkaProducer.stopped += 1


def test_consumer_without_committed_offset_starts_from_oldest_message(monkeypatch):
    created_with = {}

    def fake_kafka_consumer(*topics, **config):
        created_with.update(config)
        return SimpleNamespace()

    monkeypatch.setattr(async_kafka_consumer, "AIOKafkaConsumer", fake_kafka_consumer)

    AsyncKafkaConsumer()

    assert created_with["auto_offset_reset"] == "earliest"
    assert created_with["enable_auto_commit"] is False


async def test_producers_drop_duplicates_from_network_retries(monkeypatch):
    configs = []

    class RecordingAIOKafkaProducer(FakeAIOKafkaProducer):
        def __init__(self, **kwargs) -> None:
            configs.append(kwargs)

    monkeypatch.setattr(FakeAIOKafkaProducer, "fail_start", False)
    monkeypatch.setattr(async_kafka_producer, "AIOKafkaProducer", RecordingAIOKafkaProducer)
    monkeypatch.setattr(outbox, "AIOKafkaProducer", RecordingAIOKafkaProducer)
    monkeypatch.setattr(AsyncKafkaProducer, "_producer", None)

    await AsyncKafkaProducer.init()
    await AsyncKafkaProducer.stop()
    outbox.default_producer()

    assert len(configs) == 2
    for config in configs:
        assert config["enable_idempotence"] is True
        assert config["acks"] == "all"


async def test_producer_is_not_marked_ready_after_failed_start(monkeypatch):
    monkeypatch.setattr(async_kafka_producer, "AIOKafkaProducer", FakeAIOKafkaProducer)
    monkeypatch.setattr(AsyncKafkaProducer, "_producer", None)
    FakeAIOKafkaProducer.fail_start = True
    FakeAIOKafkaProducer.stopped = 0

    with pytest.raises(ConnectionError):
        await AsyncKafkaProducer.init()
    assert AsyncKafkaProducer._producer is None
    assert FakeAIOKafkaProducer.stopped == 1

    FakeAIOKafkaProducer.fail_start = False
    await AsyncKafkaProducer.init()
    assert AsyncKafkaProducer._producer is not None

    await AsyncKafkaProducer.stop()
    assert AsyncKafkaProducer._producer is None


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port) -> None:
        self.calls = []
        self.closed = False
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc) -> None:
        self.closed = True

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user, password) -> None:
        self.calls.append("login")

    def sendmail(self, sender, recipient, body) -> dict:
        self.calls.append(("sendmail", recipient))
        return {}


async def test_email_uses_one_closed_connection_per_message(monkeypatch, test_user):
    FakeSMTP.instances = []
    monkeypatch.setattr(mail_service.smtplib, "SMTP", FakeSMTP)
    service = mail_service.EmailService(test_user)

    assert await service.send_welcome_email() is True
    assert await service.send_verification_email("http://x") is True

    assert len(FakeSMTP.instances) == 2
    for smtp in FakeSMTP.instances:
        assert smtp.calls == ["starttls", "login", ("sendmail", test_user.email)]
        assert smtp.closed is True


def test_email_subjects_match_their_content(test_user):
    service = mail_service.EmailService(test_user)

    assert service._generate_verification_email("http://x")["Subject"] == "Account verification"
    assert service._generate_welcome_email()["Subject"] == "Welcome to Blog service"


async def test_search_outage_returns_503():
    class FailingRepository:
        async def search(self, query: str):
            raise ElasticConnectionError("elasticsearch down")

    with pytest.raises(HTTPException) as exc_info:
        await PostService(FailingRepository(), outbox_repository=None, uow=None).search("anything")

    assert exc_info.value.status_code == 503
