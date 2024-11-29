import json
import logging
from typing import List, Annotated

from fastapi import (
    APIRouter, Query,
)
from starlette import status
import aioredis

from app.core.auth.dependencies import CurrentUserDependency
from app.core.config import settings
from app.dependencies.services import PostServiceDependency, CommentServiceDependency
from app.schemas.comment import CommentRead, PaginatedComments, CommentFilterParams
from app.schemas.post import Post, PostUpdate, PaginatedPosts, PostFilterParams
from app.schemas.post import PostRead

router = APIRouter()
redis = aioredis.from_url(settings.redis_cache_url)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@router.post("/", response_model=PostRead)
async def create_post(
    post: Post,
    current_user: CurrentUserDependency,
    service: PostServiceDependency
):
    return await service.create(
        post, current_user
    )


@router.get("/", response_model=PaginatedPosts)
async def get_posts(
    current_user: CurrentUserDependency,
    service: PostServiceDependency,
    fileter_params: Annotated[PostFilterParams, Query()]
):
    logger.debug(fileter_params)
    redis_key = f"get-posts-page-{fileter_params.page}-{fileter_params.limit}"
    cached_page = await redis.get(
        redis_key
    )
    if cached_page:
        logger.debug(f"Got cached data from redis: {cached_page}")
        return json.loads(cached_page.decode("utf-8"))

    response = await service.get_list(
        fileter_params
    )
    await redis.set(
        redis_key,
        response.model_dump_json(),
        ex=60
    )
    return response


@router.get("/search", response_model=List[PostRead])
async def search_posts(
    query: str,
    current_user: CurrentUserDependency,
    service: PostServiceDependency,

):
    return await service.search(query)


@router.get("/{post_id}", response_model=PostRead)
async def get_post(
    post_id: int,
    current_user: CurrentUserDependency,
    service: PostServiceDependency
):
    return await service.get_by_id(post_id)


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post: PostUpdate,
    current_user: CurrentUserDependency,
    service: PostServiceDependency
):
    return await service.update_by_id(
        post_id,
        post,
        current_user
    )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: CurrentUserDependency,
    service: PostServiceDependency
):
    return await service.delete_by_id(post_id, current_user)


@router.get("/{post_id:int}/comments/", response_model=PaginatedComments)
async def get_posts_comment(
    post_id: int,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency
):
    filter_params = CommentFilterParams(
        post_id=post_id
    )
    return await service.get_list(filter_params)
