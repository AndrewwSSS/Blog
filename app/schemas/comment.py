from datetime import datetime

from pydantic import BaseModel


class Comment(BaseModel):
    content: str
    post_id: int


class CommentRead(Comment):
    id: int
    owner_id: int
    date_posted: datetime

    class Config:
        from_attributes = True


class CommentUpdate(Comment):
    title: str | None = None
    content: str | None = None
