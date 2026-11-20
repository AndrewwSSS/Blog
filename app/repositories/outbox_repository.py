from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import utc_now
from app.models import OutboxEventDB

TASK_TOPIC_PREFIX = "celery:"


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, topic: str, payload: dict) -> OutboxEventDB:
        """Stage an event in the current transaction; the unit of work commits it."""
        event = OutboxEventDB(topic=topic, payload=payload)
        self.session.add(event)
        return event

    def add_task(self, task_name: str, *args, eta: datetime | None = None) -> OutboxEventDB:
        """Stage a Celery task; it is sent only after the transaction commits."""
        payload: dict = {"args": list(args)}
        if eta is not None:
            payload["eta"] = eta.isoformat()
        return self.add(f"{TASK_TOPIC_PREFIX}{task_name}", payload)

    async def lock_pending(self, limit: int) -> list[OutboxEventDB]:
        """Lock the oldest unpublished events; rows locked by another relay are skipped."""
        query = (
            select(OutboxEventDB)
            .where(OutboxEventDB.published_at.is_(None))
            .order_by(OutboxEventDB.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_published(self, events: list[OutboxEventDB]) -> None:
        now = utc_now()
        for event in events:
            event.published_at = now

    async def delete_published_before(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            delete(OutboxEventDB).where(OutboxEventDB.published_at < cutoff)
        )
        return result.rowcount
