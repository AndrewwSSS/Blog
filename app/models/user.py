from sqlalchemy import Integer, String, Boolean, Float
from sqlalchemy.orm import mapped_column, relationship, Mapped
from typing import TYPE_CHECKING
from app.db.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.post import PostDB
    from app.models.comment import CommentDB


class UserDB(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    post_auto_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_after: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    posts: Mapped[list["PostDB"]] = relationship("PostDB", back_populates="owner")
    comments: Mapped[list["CommentDB"]] = relationship("CommentDB", back_populates="owner")

    def __repr__(self) -> str:
        return f"<UserDB(id={self.id}, username={self.username}, email={self.email})>"
