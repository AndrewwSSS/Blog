from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel
from pydantic import ConfigDict


class Comment(BaseModel):
    content: str
    post_id: int


class CommentRead(Comment):
    id: int
    owner_id: int
    date_posted: datetime
    is_blocked: bool

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class CommentUpdate(Comment):
    title: str | None = None
    content: str | None = None
