from app.repositories.post_repository import PostRepository
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import UserRead
from app.core.config import settings
from app.tasks.init import create_reply_for_post


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.repository = post_repository

    async def get_posts(self) -> [PostRead]:
        return await self.repository.get_posts()

    async def create_post(self, post: Post, user: UserRead) -> PostRead:
        post = await self.repository.create_post(
            post,
            user.id,
            settings.CONTENT_VALIDATOR_CLASS
        )
        if user.post_auto_reply:
            create_reply_for_post.apply_async(
                args=(post.id,),
                countdown=int(user.reply_after)
            )
        return post
