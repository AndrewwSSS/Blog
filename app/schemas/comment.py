from datetime import datetime
from typing import ClassVar, List

from pydantic import BaseModel, Field, model_validator
from pydantic import ConfigDict

from app.schemas.types import UTCDatetime


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
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=5, ge=1, le=100)
    date_from: UTCDatetime | None = None
    date_to: UTCDatetime | None = None
    owner_id: int | None = Field(None, ge=1)
    post_id: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def check_date_range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be earlier than or equal to date_to.")
        return self


class PaginatedComments(BaseModel):
    items: List[CommentRead]
    total_pages: int
    current_page: int
    limit: int
