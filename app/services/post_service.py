import logging

from fastapi import HTTPException
from starlette import status

from app.core.config import settings
from app.core.utils import PagePaginator
from app.repositories.post_repository import PostRepository
from app.schemas.post import (
    Post,
    PostUpdate,
    PostInDB,
    PostRead, PaginatedPosts, PostFilterParams
)
from app.schemas.user import UserInDB
from app.celery.tasks import (
    create_reply_for_post,
    validate_post_content,
    add_post_to_elastic_search,
    update_post_document,
    delete_post_document
)

logger = logging.getLogger(__name__)


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.repository = post_repository

    async def get_list(
        self,
        filter_params: PostFilterParams
    ) -> PaginatedPosts:

        count_total_items = await self.repository.count_records()
        paginator = PagePaginator(
            filter_params.page,
            filter_params.limit,
            count_total_items,
        )

        results = await self.repository.get_list(
            offset=paginator.offset,
            **filter_params.dict(exclude_none=True, exclude={"page"}),
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

        validate_post_content.delay(post.id)
        if user.post_auto_reply:
            create_reply_for_post.apply_async(
                args=(post.id,),
                countdown=int(user.reply_after)
            )
        add_post_to_elastic_search.delay(post.id)

        return post

    async def get_by_id(self, post_id: int) -> PostInDB:
        post = await self.repository.get_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )
        return post

    async def update_by_id(
        self,
        post_id: int,
        post: PostUpdate,
        current_user: UserInDB
    ) -> PostInDB:

        post_to_update = await self.get_by_id(post_id)

        if current_user.id != post_to_update.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to update post with id {post_id}"
            )

        updated = await self.repository.update_by_id(
            record_id=post_id,
            **post.model_dump(exclude_none=True),
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post with id {post_id} not found"
            )

        update_post_document.delay(post_id)
        return await self.repository.get_by_id(post_id)

    async def delete_by_id(
        self,
        post_id: int,
        user: UserInDB
    ) -> None:
        post_to_delete = await self.get_by_id(post_id)

        if user.id != post_to_delete.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to delete post with id {post_id}"
            )

        await self.repository.delete_by_id(post_id)

        delete_post_document.delay(post_id)

    async def validate_content(self, post_id: int) -> None:
        post = await self.repository.get_by_id(post_id)
        if not post:
            raise ValueError("Post not found")
        validator = settings.CONTENT_VALIDATOR_CLASS()
        is_validated = await validator.validate_post(
            post.content, post.title,
        )

        if not is_validated:
            await self.repository.update_by_id(
                post_id, {"is_blocked": True}
            )
            logger.info(f"Post: {post.id} has been blocked")

    async def search(self, query: str) -> [PostRead]:
        return await self.repository.search(query)
