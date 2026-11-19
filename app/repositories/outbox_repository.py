from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEventDB


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, topic: str, payload: dict) -> OutboxEventDB:
        """Stage an event in the current transaction; the caller commits."""
        event = OutboxEventDB(topic=topic, payload=payload)
        self.session.add(event)
        return event

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
        now = datetime.utcnow()
        for event in events:
            event.published_at = now
        await self.session.commit()

    async def delete_published_before(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            delete(OutboxEventDB).where(OutboxEventDB.published_at < cutoff)
        )
        await self.session.commit()
        return result.rowcount
