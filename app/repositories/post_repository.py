from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
            PostRead.model_validate(city[0])
            for city in post_list.fetchall()
        ]

    async def create_post(self, post: Post, user: UserRead) -> PostRead:
        post_db = PostDB(
            **post.dict(),
            owner_id=user.id
        )
        self.session.add(post_db)
        await self.session.commit()
        await self.session.refresh(post_db)

        return PostRead.model_validate(
            post_db
        )
