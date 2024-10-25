from app.core.config import settings
from app.repositories.post_repository import PostRepository
from app.schemas.post import Post
from app.schemas.post import PostRead
from app.schemas.user import UserRead
from app.tasks.init import create_reply_for_post, validate_post_content


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.repository = post_repository

    async def get_posts(self) -> [PostRead]:
        return await self.repository.get_posts()

    async def create_post(self, post: Post, user: UserRead) -> PostRead:
        post = await self.repository.create_post(
            post,
            user.id,
        )
        validate_post_content.delay(post.id)
        if user.post_auto_reply:
            create_reply_for_post.apply_async(
                args=(post.id,),
                countdown=int(user.reply_after)
            )
        return post

    async def validate_post_content(self, post_id: int) -> None:
        post = await self.repository.get_postDb_by_id(post_id)
        if not post:
            raise ValueError("Post not found")
        validator = settings.CONTENT_VALIDATOR_CLASS()
        is_validated = await validator.validate_post(
            post.content, post.title,
        )

        if not is_validated:
            await self.repository.update_post(
                post_id, {"is_blocked": True}
            )
            print(f"Post: {post.id} has been blocked")
