from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.posts import get_posts
from app.core import cache
from app.core.validation.base_content_validator import BaseContentValidator
from app.repositories.post_repository import PostRepository
from app.schemas.post import PaginatedPosts, PostFilterParams, PostInDB
from app.services import moderation
from app.db.unit_of_work import UnitOfWork


class CountingPostService:
    def __init__(self) -> None:
        self.calls = 0

    async def get_list(self, filter_params: PostFilterParams) -> PaginatedPosts:
        self.calls += 1
        return PaginatedPosts(
            items=[], total_pages=0, current_page=filter_params.page, limit=filter_params.limit
        )


class BrokenRedis:
    async def get(self, key):
        raise RedisConnectionError("down")

    async def set(self, key, value, ex=None):
        raise RedisConnectionError("down")

    async def incr(self, key):
        raise RedisConnectionError("down")


async def test_second_request_is_served_from_cache():
    service = CountingPostService()
    params = PostFilterParams(page=1, limit=5)

    first = await get_posts(None, service, params)
    second = await get_posts(None, service, params)

    assert service.calls == 1
    assert second == first.model_dump(mode="json")


async def test_filters_are_part_of_cache_key():
    service = CountingPostService()

    await get_posts(None, service, PostFilterParams(page=1, limit=5))
    await get_posts(None, service, PostFilterParams(page=1, limit=5, owner_id=7))

    assert service.calls == 2


async def test_invalidation_makes_cached_pages_stale():
    service = CountingPostService()
    params = PostFilterParams(page=1, limit=5)

    await get_posts(None, service, params)
    await cache.invalidate_posts_cache()
    await get_posts(None, service, params)

    assert service.calls == 2


async def test_redis_outage_falls_back_to_database(monkeypatch):
    monkeypatch.setattr(cache, "redis", BrokenRedis())
    service = CountingPostService()
    params = PostFilterParams(page=1, limit=5)

    await get_posts(None, service, params)
    await get_posts(None, service, params)
    await cache.invalidate_posts_cache()

    assert service.calls == 2


async def test_blocking_a_post_invalidates_cache(
    test_post: PostInDB,
    session: AsyncSession,
    uow: UnitOfWork,
    monkeypatch,
):
    class RejectAllValidator(BaseContentValidator):
        async def validate_post(self, content: str, title: str) -> bool:
            return False

        async def validate_comment(self, content: str) -> bool:
            return False

    monkeypatch.setattr(moderation, "get_content_validator", RejectAllValidator)
    key_before = await cache.posts_page_key(PostFilterParams())

    await moderation.moderate_post(PostRepository(session), uow, test_post.id)
    assert await cache.posts_page_key(PostFilterParams()) == key_before

    await uow.commit()
    assert await cache.posts_page_key(PostFilterParams()) != key_before
