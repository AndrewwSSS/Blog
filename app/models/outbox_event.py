from datetime import datetime

from sqlalchemy import JSON, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.utils import utc_now
from app.db.base_model import BaseModel
from app.db.types import UTCDateTime


class OutboxEventDB(BaseModel):
    """An event saved in the same transaction as the data it describes.

    The outbox relay publishes rows with published_at IS NULL to Kafka.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_unpublished",
            "id",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<OutboxEventDB(id={self.id}, topic={self.topic}, "
            f"published_at={self.published_at}, attempts={self.attempts})>"
        )
