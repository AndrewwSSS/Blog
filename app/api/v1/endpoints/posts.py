import json
import logging
from typing import List, Annotated

from fastapi import (
    APIRouter,
    Query,
)
from starlette import status

from app.core.auth.dependencies import CurrentUserDependency
from app.core.cache import (
    POSTS_CACHE_TTL_SECONDS,
    get_cached,
    posts_page_key,
    set_cached,
)
from app.dependencies.services import PostServiceDependency, CommentServiceDependency
from app.schemas.comment import PaginatedComments, CommentFilterParams
from app.schemas.post import Post, PostUpdate, PaginatedPosts, PostFilterParams
from app.schemas.post import PostRead

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/", response_model=PostRead)
async def create_post(
    post: Post, current_user: CurrentUserDependency, service: PostServiceDependency
):
    return await service.create(post, current_user)


@router.get("/", response_model=PaginatedPosts)
async def get_posts(
    current_user: CurrentUserDependency,
    service: PostServiceDependency,
    filter_params: Annotated[PostFilterParams, Query()],
):
    cache_key = await posts_page_key(filter_params)
    cached_page = await get_cached(cache_key)
    if cached_page:
        logger.debug(f"Posts page served from cache: {cache_key}")
        return json.loads(cached_page)

    response = await service.get_list(filter_params)
    await set_cached(cache_key, response.model_dump_json(), POSTS_CACHE_TTL_SECONDS)
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
    post_id: int, current_user: CurrentUserDependency, service: PostServiceDependency
):
    return await service.get_by_id(post_id)


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post: PostUpdate,
    current_user: CurrentUserDependency,
    service: PostServiceDependency,
):
    return await service.update_by_id(post_id, post, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int, current_user: CurrentUserDependency, service: PostServiceDependency
):
    return await service.delete_by_id(post_id, current_user)


@router.get("/{post_id}/comments/", response_model=PaginatedComments)
async def get_posts_comment(
    post_id: int,
    current_user: CurrentUserDependency,
    service: CommentServiceDependency,
    filter_params: Annotated[CommentFilterParams, Query()],
):
    filter_params.post_id = post_id
    return await service.get_list(filter_params)
