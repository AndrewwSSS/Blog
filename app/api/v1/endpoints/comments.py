from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.auth.dependencies import get_current_user
from app.dependencies.services import get_comment_service
from app.schemas.analytics import CommentAnalytic, CommentsAnalyticsRequest
from app.schemas.comment import Comment
from app.schemas.comment import CommentRead
from app.schemas.user import UserRead
from app.services.comment_service import CommentService

router = APIRouter()


@router.post("/", response_model=CommentRead)
async def create_comment(
    comment: Comment,
    user: UserRead = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.create_comment(
        comment, user
    )


@router.get("/", response_model=List[CommentRead])
async def get_posts(
    user: UserRead = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.get_comments()


@router.get("/comments-daily-breakdown", response_model=List[CommentAnalytic])
async def get_comments_daily_breakdown(
    date_from: date = Query(..., description="Start date for the analytics in YYYY-MM-DD format"),
    date_to: date = Query(..., description="End date for the analytics in YYYY-MM-DD format"),
    user: UserRead = Depends(get_current_user),
    service: CommentService = Depends(get_comment_service)
):
    return await service.get_comments_analytics(
        date_from, date_to
    )
