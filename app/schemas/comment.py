from datetime import datetime
from typing import ClassVar, List

from pydantic import BaseModel, Field
from pydantic import ConfigDict


class CommentCreate(BaseModel):
    content: str
    post_id: int


class CommentRead(BaseModel):
    id: int
    content: str
    post_id: int
    owner_id: int
    date_posted: datetime
    is_blocked: bool

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class CommentUpdate(BaseModel):
    content: str


class CommentInDB(BaseModel):
    id: int
    content: str
    owner_id: int
    date_posted: datetime
    is_blocked: bool
    post_id: int

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class CommentFilterParams(BaseModel):
    page: int | None = 1
    limit: int | None = 5
    date_from: datetime | None = None
    date_to: datetime | None = None
    owner_id: int | None = Field(None, ge=1)
    post_id: int | None = Field(None, ge=1)


class PaginatedComments(BaseModel):
    items: List[CommentRead]
    total_pages: int
    current_page: int
    limit: int
