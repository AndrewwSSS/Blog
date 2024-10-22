from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.validation.base_content_validator import BaseContentValidator
from app.models import PostDB
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import UserRead


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_posts(self) -> [PostRead]:
        query = select(PostDB)
        post_list = await self.session.execute(query)
        return [
            PostRead.model_validate(post[0])
            for post in post_list.fetchall()
        ]

    async def create_post(
        self,
        post: Post,
        user: UserRead,
        content_validator_class: Type[BaseContentValidator]
    ) -> PostRead:
        content_validator = content_validator_class()
        is_validated = await content_validator.validate_post(
            post.content, post.title
        )

        post_db = PostDB(
            **post.dict(),
            owner_id=user.id,
            is_blocked=not is_validated
        )

        self.session.add(post_db)
        await self.session.commit()
        await self.session.refresh(post_db)

        return PostRead.model_validate(
            post_db
        )
