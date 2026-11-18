from pydantic import BaseModel
from datetime import date


class CommentAnalytic(BaseModel):
    date: date
    total_comments: int
    blocked_comments: int
