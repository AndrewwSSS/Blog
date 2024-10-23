from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel
from pydantic import ConfigDict


class Post(BaseModel):
    title: str
    content: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class PostRead(Post):
    id: int
    owner_id: int
    date_posted: datetime
    is_blocked: bool

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class PostUpdate(Post):
    title: str | None = None
    content: str | None = None
