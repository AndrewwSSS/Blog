import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEventDB
from app.repositories.outbox_repository import OutboxRepository
from tests.fixtures import IS_SQLITE, async_session_maker

pytestmark = pytest.mark.skipif(IS_SQLITE, reason="needs PostgreSQL (set TEST_DATABASE_URL)")

UTC_COLUMNS = [
    ("posts", "date_posted"),
    ("comments", "date_posted"),
    ("outbox_events", "created_at"),
    ("outbox_events", "published_at"),
]


async def test_relays_never_lock_the_same_events():
    async with async_session_maker() as session:
        session.add_all(OutboxEventDB(topic="t", payload={"n": n}) for n in range(3))
        await session.commit()

    async with async_session_maker() as first, async_session_maker() as second:
        first_batch = await OutboxRepository(first).lock_pending(limit=2)
        second_batch = await OutboxRepository(second).lock_pending(limit=10)

        assert [event.payload["n"] for event in first_batch] == [0, 1]
        assert [event.payload["n"] for event in second_batch] == [2]
        await first.rollback()
        await second.rollback()


async def test_unpublished_index_is_partial(session: AsyncSession):
    result = await session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_outbox_events_unpublished'")
    )

    assert "WHERE (published_at IS NULL)" in result.scalar_one()


@pytest.mark.parametrize("table, column", UTC_COLUMNS)
async def test_datetime_columns_are_timestamptz(session: AsyncSession, table: str, column: str):
    result = await session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )

    assert result.scalar_one() == "timestamp with time zone"


async def test_sessions_run_in_utc(session: AsyncSession):
    assert (await session.execute(text("SHOW timezone"))).scalar_one() == "UTC"
