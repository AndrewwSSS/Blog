import json
import logging
from collections.abc import Callable
from datetime import timedelta

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.utils import utc_now
from app.db.unit_of_work import UnitOfWork
from app.models import OutboxEventDB
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)

RELAY_BATCH_SIZE = 100
PUBLISHED_RETENTION = timedelta(days=7)
MAX_ERROR_LENGTH = 1000


def _serialize(event: OutboxEventDB) -> str:
    return json.dumps(event.payload)


def default_producer() -> AIOKafkaProducer:
    return AIOKafkaProducer(bootstrap_servers=settings.KAFKA_URL, acks="all")


async def publish_now(
    uow: UnitOfWork, outbox: OutboxRepository, events: list[OutboxEventDB]
) -> None:
    """Try to publish committed events right away; meant to run after the commit.

    Best effort: on any failure the events stay pending and the relay retries them.
    """
    try:
        for event in events:
            await AsyncKafkaProducer.publish(event.topic, _serialize(event))
        await outbox.mark_published(events)
        await uow.commit()
    except Exception:
        logger.warning("Immediate publish failed, the outbox relay will retry", exc_info=True)


async def relay_pending_events(
    outbox: OutboxRepository,
    producer_factory: Callable[[], AIOKafkaProducer] = default_producer,
    batch_size: int = RELAY_BATCH_SIZE,
) -> int:
    """Publish pending outbox events to Kafka and return how many were published.

    Run it in a unit of work: its commit saves the results and releases the row locks.
    """
    events = await outbox.lock_pending(batch_size)
    if not events:
        return 0

    producer = producer_factory()
    published = []
    try:
        await producer.start()
    except Exception:
        logger.warning(
            f"Kafka unavailable, {len(events)} outbox events stay pending", exc_info=True
        )
        await producer.stop()
        return 0

    try:
        for event in events:
            try:
                await producer.send_and_wait(event.topic, _serialize(event).encode("utf-8"))
                published.append(event)
            except Exception as e:
                event.attempts += 1
                event.last_error = repr(e)[:MAX_ERROR_LENGTH]
                logger.error(
                    f"Failed to publish outbox event {event.id} (attempt {event.attempts})"
                )
    finally:
        await producer.stop()

    await outbox.mark_published(published)
    return len(published)


async def delete_old_published_events(outbox: OutboxRepository) -> int:
    return await outbox.delete_published_before(utc_now() - PUBLISHED_RETENTION)
