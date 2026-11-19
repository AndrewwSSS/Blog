from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]
"""A datetime converted to aware UTC; naive input is read as UTC."""
