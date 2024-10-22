from app.repositories.post_repository import PostRepository
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import UserRead
from app.core.config import settings


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.repository = post_repository

    async def get_posts(self) -> [PostRead]:
        return await self.repository.get_posts()

    async def create_post(self, post: Post, user: UserRead) -> PostRead:

        return await self.repository.create_post(
            post,
            user,
            settings.CONTENT_VALIDATOR_CLASS
        )
