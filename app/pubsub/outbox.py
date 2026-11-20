import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from aiokafka import AIOKafkaProducer

from app.celery.app import celery
from app.core.config import settings
from app.core.utils import utc_now
from app.db.unit_of_work import UnitOfWork
from app.models import OutboxEventDB
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.repositories.outbox_repository import TASK_TOPIC_PREFIX, OutboxRepository

logger = logging.getLogger(__name__)

RELAY_BATCH_SIZE = 100
PUBLISHED_RETENTION = timedelta(days=7)
MAX_ERROR_LENGTH = 1000


def _serialize(event: OutboxEventDB) -> str:
    return json.dumps(event.payload)


def _is_task(event: OutboxEventDB) -> bool:
    return event.topic.startswith(TASK_TOPIC_PREFIX)


def _send_task(event: OutboxEventDB) -> None:
    eta = event.payload.get("eta")
    celery.send_task(
        event.topic.removeprefix(TASK_TOPIC_PREFIX),
        args=event.payload["args"],
        eta=datetime.fromisoformat(eta) if eta else None,
    )


def _record_failure(event: OutboxEventDB, error: Exception) -> None:
    event.attempts += 1
    event.last_error = repr(error)[:MAX_ERROR_LENGTH]
    logger.error(f"Failed to send outbox event {event.id} (attempt {event.attempts})")


def default_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(bootstrap_servers=settings.KAFKA_URL, acks="all")


async def publish_now(
    uow: UnitOfWork, outbox: OutboxRepository, events: list[OutboxEventDB]
) -> None:
    """Try to send committed events right away; meant to run after the commit.

    Best effort: on any failure the events stay pending and the relay retries them.
    """
    try:
        for event in events:
            if _is_task(event):
                _send_task(event)
            else:
                await AsyncKafkaProducer.publish(event.topic, _serialize(event))
        await outbox.mark_published(events)
        await uow.commit()
    except Exception:
        logger.warning("Immediate send failed, the outbox relay will retry", exc_info=True)


def _send_tasks(events: list[OutboxEventDB]) -> list[OutboxEventDB]:
    sent = []
    for event in events:
        try:
            _send_task(event)
            sent.append(event)
        except Exception as e:
            _record_failure(event, e)
    return sent


async def _publish_messages(
    events: list[OutboxEventDB], producer_factory: Callable[[], AIOKafkaProducer]
) -> list[OutboxEventDB]:
    if not events:
        return []

    producer = producer_factory()
    try:
        await producer.start()
    except Exception:
        logger.warning(
            f"Kafka unavailable, {len(events)} outbox events stay pending", exc_info=True
        )
        await producer.stop()
        return []

    published = []
    try:
        for event in events:
            try:
                await producer.send_and_wait(event.topic, _serialize(event).encode("utf-8"))
                published.append(event)
            except Exception as e:
                _record_failure(event, e)
    finally:
        await producer.stop()
    return published


async def relay_pending_events(
    outbox: OutboxRepository,
    producer_factory: Callable[[], AIOKafkaProducer] = default_producer,
    batch_size: int = RELAY_BATCH_SIZE,
) -> int:
    """Send pending outbox events and return how many were sent.

    Celery tasks and Kafka messages are sent independently, so an outage of one
    does not hold back the other. Run it in a unit of work: its commit saves the
    results and releases the row locks.
    """
    events = await outbox.lock_pending(batch_size)
    sent = _send_tasks([event for event in events if _is_task(event)])
    sent += await _publish_messages(
        [event for event in events if not _is_task(event)], producer_factory
    )
    await outbox.mark_published(sent)
    return len(sent)


async def delete_old_published_events(outbox: OutboxRepository) -> int:
    return await outbox.delete_published_before(utc_now() - PUBLISHED_RETENTION)
