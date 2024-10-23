import asyncio

from celery import Celery

from app.core.config import settings
from app.db.session import get_session
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import Comment

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
)


@celery.task
def create_reply_for_post(post_id: int):
    asyncio.run(_create_reply_for_post(post_id))


async def _create_reply_for_post(post_id: int):
    # get valid session
    session = get_session()
    # get post
    post_repo = PostRepository(session)
    post = await post_repo.get_post_by_id(post_id)
    if not post:
        raise ValueError("Post not found")

    # generate reply
    reply_generator = settings.REPLY_GENERATOR_CLASS()
    reply_content = await reply_generator.generate_post_reply(
        post.title, post.content,
    )
    user_repo = UserRepository(session)
    bot = await user_repo.get_user_by_username(
        settings.BOT_USERNAME
    )
    if not bot:
        raise ValueError("Bot not found")

    # create reply comment
    comment_repo = CommentRepository(session)
    comment = Comment(
        content=reply_content,
        owner_id=bot.id,
        post_id=post_id,
    )
    created_comment = await comment_repo.create_comment(comment)
    print(f"{created_comment=}")


