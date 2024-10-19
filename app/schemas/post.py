from datetime import datetime

from pydantic import BaseModel


class PostCreate(BaseModel):
    title: str
    content: str


class PostRead(PostCreate):
    id: int
    owner_id: int
    date_posted: datetime

    class Config:
        orm_mode = True


class PostUpdate(PostRead):
    title: str | None = None
    content: str | None = None
