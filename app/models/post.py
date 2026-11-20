from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, Boolean, Text
from sqlalchemy.orm import mapped_column, relationship, Mapped
from typing import TYPE_CHECKING
from app.core.utils import utc_now
from app.db.base_model import BaseModel
from app.db.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.user import UserDB
    from app.models.comment import CommentDB


class PostDB(BaseModel):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_posted: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    auto_replied_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    owner: Mapped["UserDB"] = relationship("UserDB", back_populates="posts")
    comments: Mapped[list["CommentDB"]] = relationship(
        "CommentDB",
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PostDB(id={self.id}, "
            f"title={self.title}, "
            f"owner_id={self.owner_id}, "
            f"is_blocked={self.is_blocked})>"
        )
