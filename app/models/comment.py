from datetime import datetime
from sqlalchemy import (
    Integer,
    ForeignKey,
    DateTime,
    Boolean,
    Text
)
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship, Mapped
from typing import TYPE_CHECKING
from app.db.base_model import BaseModel


if TYPE_CHECKING:
    from app.models.user import UserDB
    from app.models.post import PostDB


class CommentDB(BaseModel):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), nullable=False)
    date_posted: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    owner: Mapped["UserDB"] = relationship("UserDB", back_populates="comments")
    post: Mapped["PostDB"] = relationship("PostDB", back_populates="comments")

    def __repr__(self) -> str:
        return (f"<CommentDB(id={self.id}, "
                f"owner_id={self.owner_id}, "
                f"post_id={self.post_id}, "
                f"is_blocked={self.is_blocked})>")
