from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import PostDB
from app.schemas.post import Post
from app.schemas.post import PostRead


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
        user_id: int,
    ) -> PostRead:
        post_db = PostDB(
            **post.model_dump(),
            owner_id=user_id,
        )

        self.session.add(post_db)
        await self.session.commit()
        await self.session.refresh(post_db)

        return PostRead.model_validate(
            post_db
        )

    async def get_post_by_id(self, post_id: int) -> PostRead | None:
        query = select(PostDB).where(PostDB.id == post_id)
        result = await self.session.execute(query)
        post_db = result.scalar_one_or_none()
        if post_db:
            return PostRead.model_validate(post_db)

    async def get_postDb_by_id(self, post_id: int) -> PostDB | None:
        query = select(PostDB).where(PostDB.id == post_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
