import logging
from datetime import timedelta

from elasticsearch import ApiError, TransportError
from fastapi import HTTPException
from starlette import status

from app.core.cache import invalidate_posts_cache
from app.core.utils import PagePaginator
from app.db.unit_of_work import UnitOfWork
from app.pubsub.outbox import publish_now
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.post_repository import PostRepository
from app.schemas.post import Post, PostUpdate, PostInDB, PaginatedPosts, PostFilterParams
from app.schemas.user import UserInDB
from app.celery.tasks import (
    create_reply_for_post,
    validate_post_content,
    add_post_to_elastic_search,
    update_post_document,
    delete_post_document,
)

logger = logging.getLogger(__name__)


class PostService:
    def __init__(
        self, post_repository: PostRepository, outbox_repository: OutboxRepository, uow: UnitOfWork
    ) -> None:
        self.repository = post_repository
        self.outbox = outbox_repository
        self.uow = uow

    async def get_list(self, filter_params: PostFilterParams) -> PaginatedPosts:

        filters = filter_params.model_dump(exclude_none=True, exclude={"page", "limit"})
        paginator = PagePaginator(
            filter_params.page,
            filter_params.limit,
            await self.repository.count_list(**filters),
        )

        results = await self.repository.get_list(
            offset=paginator.offset,
            limit=paginator.limit,
            **filters,
        )

        return PaginatedPosts(
            items=results,
            total_pages=paginator.total_pages,
            current_page=paginator.page,
            limit=paginator.limit,
        )

    async def create(self, post: Post, user: UserInDB) -> PostInDB:
        post = await self.repository.create(
            **post.model_dump(),
            owner_id=user.id,
        )
        events = [
            self.outbox.add_task(validate_post_content.name, post.id),
            self.outbox.add_task(add_post_to_elastic_search.name, post.id),
        ]
        if user.post_auto_reply:
            reply_at = post.date_posted + timedelta(seconds=user.reply_after)
            events.append(self.outbox.add_task(create_reply_for_post.name, post.id, eta=reply_at))
        self.uow.after_commit(invalidate_posts_cache)
        self.uow.after_commit(publish_now, self.uow, self.outbox, events)

        return post

    async def get_by_id(self, post_id: int, include_blocked: bool = False) -> PostInDB:
        post = await self.repository.get_by_id(post_id)
        if not post or (post.is_blocked and not include_blocked):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found"
            )
        return post

    async def update_by_id(
        self, post_id: int, post: PostUpdate, current_user: UserInDB
    ) -> PostInDB:

        post_to_update = await self.get_by_id(post_id, include_blocked=True)

        if current_user.id != post_to_update.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to update post with id {post_id}",
            )

        updated = await self.repository.update_by_id(
            record_id=post_id,
            **post.model_dump(exclude_none=True),
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found"
            )

        events = [
            self.outbox.add_task(validate_post_content.name, post_id),
            self.outbox.add_task(update_post_document.name, post_id),
        ]
        self.uow.after_commit(invalidate_posts_cache)
        self.uow.after_commit(publish_now, self.uow, self.outbox, events)
        return await self.repository.get_by_id(post_id)

    async def delete_by_id(self, post_id: int, user: UserInDB) -> None:
        post_to_delete = await self.get_by_id(post_id, include_blocked=True)

        if user.id != post_to_delete.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to delete post with id {post_id}",
            )

        await self.repository.delete_by_id(post_id)
        event = self.outbox.add_task(delete_post_document.name, post_id)
        self.uow.after_commit(invalidate_posts_cache)
        self.uow.after_commit(publish_now, self.uow, self.outbox, [event])

    async def search(self, query: str) -> list[PostInDB]:
        try:
            return await self.repository.search(query)
        except (ApiError, TransportError) as e:
            logger.exception("Elasticsearch search failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search is temporarily unavailable",
            ) from e
