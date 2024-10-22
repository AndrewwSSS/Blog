from pydantic import BaseModel
from datetime import datetime, date


class CommentsAnalyticsRequest(BaseModel):
    date_from: datetime
    date_to: datetime


class CommentAnalytic(BaseModel):
    date: date
    total_comments: int
    blocked_comments: int
