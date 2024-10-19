from datetime import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    content: str
    post_id: int


class CommentRead(CommentCreate):
    id: int
    owner_id: int
    date_posted: datetime

    class Config:
        orm_mode = True


class CommentUpdate(CommentCreate):
    title: str | None = None
    content: str | None = None
