from typing import List

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.dependencies.services import get_comment_service
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
