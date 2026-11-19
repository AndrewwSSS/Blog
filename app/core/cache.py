import logging

from pydantic import BaseModel
from redis import asyncio as redis_asyncio
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

POSTS_CACHE_TTL_SECONDS = 60
POSTS_VERSION_KEY = "posts:version"

redis = redis_asyncio.from_url(settings.redis_cache_url)


async def posts_page_key(filter_params: BaseModel) -> str:
    """Build the cache key for one posts page.

    The key contains the posts version, so bumping it with
    invalidate_posts_cache() makes all older pages unreachable.
    """
    try:
        version = int(await redis.get(POSTS_VERSION_KEY) or 0)
    except RedisError as e:
        logger.warning(f"Redis unavailable, reading posts version failed: {e}")
        version = 0
    return f"posts:v{version}:{filter_params.model_dump_json()}"


async def get_cached(key: str) -> bytes | None:
    """Return the cached value, or None on a miss or a Redis error."""
    try:
        return await redis.get(key)
    except RedisError as e:
        logger.warning(f"Redis unavailable, cache read skipped: {e}")
        return None


async def set_cached(key: str, value: str, ttl_seconds: int) -> None:
    """Store a value; a Redis error is logged and ignored."""
    try:
        await redis.set(key, value, ex=ttl_seconds)
    except RedisError as e:
        logger.warning(f"Redis unavailable, cache write skipped: {e}")


async def invalidate_posts_cache() -> None:
    """Make all cached posts pages stale."""
    try:
        await redis.incr(POSTS_VERSION_KEY)
    except RedisError as e:
        logger.warning(f"Redis unavailable, posts cache not invalidated: {e}")


async def acquire_cooldown(key: str, seconds: int) -> bool:
    """Hold `key` for `seconds` if it is free.

    Returns True when the caller got the key, False when it is already held.
    A Redis error also returns False, so a rate-limited action is skipped
    rather than allowed without a limit.
    """
    try:
        return bool(await redis.set(key, "1", nx=True, ex=seconds))
    except RedisError as e:
        logger.warning(f"Redis unavailable, cooldown {key} not acquired: {e}")
        return False
