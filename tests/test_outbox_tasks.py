from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.celery.app import celery
from app.db.unit_of_work import UnitOfWork
from app.models import OutboxEventDB
from app.pubsub.outbox import relay_pending_events
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.post_repository import PostRepository
from app.schemas.post import Post
from app.schemas.user import UserInDB
from app.services.post_service import PostService
from tests.conftest import SentTask
from tests.fixtures import async_session_maker
from tests.test_outbox import FakeProducer


async def all_events() -> list[OutboxEventDB]:
    async with async_session_maker() as session:
        result = await session.execute(select(OutboxEventDB).order_by(OutboxEventDB.id))
        return list(result.scalars().all())


async def stage(*calls: tuple[str, tuple, datetime | None]) -> None:
    async with UnitOfWork(async_session_maker) as uow:
        outbox = OutboxRepository(uow.session)
        for name, args, eta in calls:
            outbox.add_task(name, *args, eta=eta)


async def relay(producer: FakeProducer) -> int:
    async with UnitOfWork(async_session_maker) as uow:
        return await relay_pending_events(OutboxRepository(uow.session), lambda: producer)


def post_service(uow: UnitOfWork) -> PostService:
    return PostService(PostRepository(uow.session), OutboxRepository(uow.session), uow)


def broker_down(monkeypatch) -> None:
    def failing_send_task(*args, **kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr(celery, "send_task", failing_send_task)


async def test_relay_sends_tasks_even_when_kafka_is_down(sent_tasks: list[SentTask]):
    await stage(("app.celery.tasks.validate_post_content", (7,), None))
    async with UnitOfWork(async_session_maker) as uow:
        OutboxRepository(uow.session).add("new-user-registration", {"id": 1})

    sent = await relay(FakeProducer(fail_start=True))

    task_event, kafka_event = await all_events()
    assert sent == 1
    assert [(t.name, t.args) for t in sent_tasks] == [
        ("app.celery.tasks.validate_post_content", (7,))
    ]
    assert task_event.published_at is not None
    assert kafka_event.published_at is None


async def test_relay_passes_the_eta(sent_tasks: list[SentTask]):
    eta = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    await stage(("app.celery.tasks.create_reply_for_post", (3,), eta))

    await relay(FakeProducer())

    [task] = sent_tasks
    assert (task.args, task.eta) == ((3,), eta)


async def test_relay_records_a_failed_task_send_and_retries_later(monkeypatch):
    await stage(("app.celery.tasks.validate_post_content", (7,), None))
    broker_down(monkeypatch)

    assert await relay(FakeProducer()) == 0

    [event] = await all_events()
    assert (event.published_at, event.attempts) == (None, 1)
    assert "broker down" in event.last_error


async def test_post_tasks_are_sent_only_after_commit(
    uow: UnitOfWork, test_user: UserInDB, monkeypatch
):
    seen = []

    def checking_send_task(name: str, args=(), eta=None, **options) -> None:
        seen.append((name.rsplit(".", 1)[-1], tuple(args)))

    monkeypatch.setattr(celery, "send_task", checking_send_task)

    post = await post_service(uow).create(Post(title="t", content="c"), test_user)
    assert seen == []
    await uow.commit()

    assert seen == [
        ("validate_post_content", (post.id,)),
        ("add_post_to_elastic_search", (post.id,)),
    ]
    assert all(event.published_at for event in await all_events())


async def test_auto_reply_eta_is_post_time_plus_delay(
    uow: UnitOfWork, test_user: UserInDB, sent_tasks: list[SentTask]
):
    user = test_user.model_copy(update={"post_auto_reply": True, "reply_after": 30.0})

    post = await post_service(uow).create(Post(title="t", content="c"), user)
    await uow.commit()

    [reply] = [t for t in sent_tasks if t.short_name == "create_reply_for_post"]
    assert reply.args == (post.id,)
    assert reply.eta == post.date_posted + timedelta(seconds=30)


async def test_tasks_survive_a_broker_outage_at_commit_time(
    uow: UnitOfWork, test_user: UserInDB, sent_tasks: list[SentTask], monkeypatch
):
    with monkeypatch.context() as patch:
        broker_down(patch)
        post = await post_service(uow).create(Post(title="t", content="c"), test_user)
        await uow.commit()
        assert all(event.published_at is None for event in await all_events())

    assert await relay(FakeProducer()) == 2

    assert sorted(t.short_name for t in sent_tasks) == [
        "add_post_to_elastic_search",
        "validate_post_content",
    ]
    assert all(t.args == (post.id,) for t in sent_tasks)
