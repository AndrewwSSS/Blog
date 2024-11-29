from datetime import date
from typing import List, Annotated

from fastapi import APIRouter, Query
from starlette import status

from app.core.auth.dependencies import CurrentUserDependency
from app.dependencies.services import CommentServiceDependency
from app.schemas.analytics import CommentAnalytic
from app.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    CommentFilterParams,
    PaginatedComments
)
from app.schemas.comment import CommentRead

router = APIRouter()


@router.post("/", response_model=CommentRead)
async def create_comment(
    comment: CommentCreate,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency
):
    return await service.create(
        comment, current_user
    )


@router.get("/", response_model=PaginatedComments)
async def get_comments(
    current_user: CurrentUserDependency,
    service: CommentServiceDependency,
    filter_params: Annotated[CommentFilterParams, Query()],
):
    return await service.get_list(
        filter_params
    )


@router.get("/comments-daily-breakdown", response_model=List[CommentAnalytic])
async def get_comments_daily_breakdown(
    current_user: CurrentUserDependency,
    service: CommentServiceDependency,
    date_from: date = Query(..., description="Start date for the analytics in YYYY-MM-DD format"),
    date_to: date = Query(..., description="End date for the analytics in YYYY-MM-DD format"),
):
    return await service.get_analytics(
        date_from, date_to
    )


@router.get("/{comment_id:int}", response_model=CommentRead)
async def get_by_id(
    comment_id: int,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency
):
    return await service.get_by_id(
        comment_id
    )


@router.patch("/{comment_id:int}", response_model=CommentRead)
async def update_comment(
    comment_id: int,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency,
    comment_update: CommentUpdate,
):
    return await service.update_by_id(
        comment_id,
        current_user,
        comment_update
    )


@router.delete("/{comment_id:int}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency,
):
    await service.delete_by_id(
        comment_id,
        current_user,
    )
