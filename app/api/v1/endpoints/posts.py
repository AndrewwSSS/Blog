from typing import List

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.dependencies.services import get_post_service
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import UserRead
from app.services.post_service import PostService

router = APIRouter()


@router.post("/", response_model=PostRead)
async def create_post(
    post: Post,
    user: UserRead = Depends(get_current_user),
    service: PostService = Depends(get_post_service)
):
    return await service.create_post(
        post, user
    )


@router.get("/", response_model=List[PostRead])
async def get_posts(
    user: UserRead = Depends(get_current_user),
    service: PostService = Depends(get_post_service)
):
    return await service.get_posts()
