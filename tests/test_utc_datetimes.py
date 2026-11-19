from datetime import UTC, datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.utils import create_access_token
from app.core.config import settings
from app.models import OutboxEventDB
from app.repositories.post_repository import PostRepository
from app.schemas.comment import CommentFilterParams
from app.schemas.post import PostFilterParams, PostInDB

PLUS_THREE = timezone(timedelta(hours=3))


async def test_datetimes_are_read_back_as_aware_utc(test_post: PostInDB, session: AsyncSession):
    post = await PostRepository(session).get_by_id(test_post.id)

    assert post.date_posted.tzinfo is UTC
    assert abs(datetime.now(UTC) - post.date_posted) < timedelta(minutes=1)


async def test_other_offsets_are_stored_as_the_same_instant(session: AsyncSession):
    moment = datetime(2026, 1, 1, 3, 0, tzinfo=PLUS_THREE)
    session.add(OutboxEventDB(topic="t", payload={}, published_at=moment))
    await session.commit()
    session.expunge_all()

    event = await session.get(OutboxEventDB, 1)

    assert event.published_at == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert event.published_at.tzinfo is UTC


async def test_naive_datetime_is_rejected_on_write(session: AsyncSession):
    session.add(OutboxEventDB(topic="t", payload={}, published_at=datetime(2026, 1, 1)))

    with pytest.raises(StatementError, match="Naive datetime"):
        await session.commit()


@pytest.mark.parametrize("params", [PostFilterParams, CommentFilterParams])
def test_filter_dates_become_utc(params):
    filters = params(date_from="2026-01-01T00:00:00", date_to="2026-01-01T05:00:00+03:00")

    assert filters.date_from == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert filters.date_to == datetime(2026, 1, 1, 2, 0, tzinfo=UTC)
    assert filters.date_to.tzinfo is UTC


@pytest.mark.parametrize("params", [PostFilterParams, CommentFilterParams])
def test_mixed_naive_and_aware_range_is_compared_not_crashing(params):
    with pytest.raises(ValidationError, match="date_from must be earlier"):
        params(date_from="2026-01-02T00:00:00", date_to="2026-01-01T23:00:00Z")


def test_access_token_expiry_is_in_the_future():
    token = create_access_token({"user_id": 1})

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["exp"] > datetime.now(UTC).timestamp()
