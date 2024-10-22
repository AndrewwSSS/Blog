from datetime import datetime

from pydantic import BaseModel


class Post(BaseModel):
    title: str
    content: str

    class Config:
        from_attributes = True


class PostRead(Post):
    id: int
    owner_id: int
    date_posted: datetime
    is_blocked: bool

    class Config:
        from_attributes = True


class PostUpdate(Post):
    title: str | None = None
    content: str | None = None
