from datetime import datetime
from typing import ClassVar, List

from pydantic import BaseModel, model_validator, Field
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

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if not (self.title or self.content):
            raise ValueError("At least one of 'title' or 'content' must be set.")
        return self


class PostInDB(BaseModel):
    id: int
    owner_id: int
    date_posted: datetime
    is_blocked: bool
    title: str
    content: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
    )


class PaginatedPosts(BaseModel):
    items: List[PostRead]
    total_pages: int
    current_page: int
    limit: int


class PostFilterParams(BaseModel):
    page: int | None = Field(default=1, ge=1)
    limit: int | None = Field(default=5, ge=1, le=100)
    owner_id: int | None = Field(default=None, ge=1)
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def check_date_from_greater_than_date_to(self):
        if not (self.date_from and self.date_to):
            return self
        if self.date_from > self.date_to:
            raise ValueError("Date must be greater than date_to.")
        return self
